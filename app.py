from flask import Flask, request, render_template, redirect, url_for, session, flash
import pandas as pd
import os
from google.cloud import storage
from send_email import send_email
from dotenv import load_dotenv
from datetime import datetime
from fuzzywuzzy import fuzz
from io import BytesIO
import json
import csv
import io

# from sentence_transformers import SentenceTransformer
# from sklearn.metrics.pairwise import cosine_similarity


# model = SentenceTransformer('intfloat/e5-small-v2')
# Load environment variables
load_dotenv()

today_date = datetime.today().strftime('%Y-%m-%d')
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecret")
USERS_STR = os.getenv('USER_DATA')
if USERS_STR:
    USERS = json.loads(USERS_STR)
    print(USERS)
else:
    print("USER_DATA not found in the environment variables.")

# Google Cloud Storage configuration
BUCKET_NAME = "scraping_revamped"

# Helper function to check credentials
def check_credentials(username, password):
    return username in USERS and USERS[username]["password"] == password

# Route: Login Page
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if check_credentials(username, password):
            session["username"] = username
            flash("Login successful!", "success")
            return redirect(url_for("search_input"))
        else:
            flash("Invalid username or password.", "danger")
    return render_template("login.html")


@app.route("/search", methods=["GET", "POST"])
def search_input():
    if "username" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        email = request.form["email"]
        if not email.endswith("@devoteam.com"):
            flash("Invalid email domain. Only emails ending with '@devoteam.com' are allowed.", "danger")
            return redirect(url_for("search_input"))
        manual_keywords = request.form.get("manual_keywords", "").strip()
        uploaded_file = request.files.get("keywords_file")
        daily_updates = request.form.get("daily_updates")  # New input field for daily updates

        # Check if neither manual keywords nor a file was provided
        if not manual_keywords and not uploaded_file:
            flash("You must enter a keyword or upload a file to proceed.", "danger")
            return redirect(url_for("search_input"))

        # If the user selected daily updates
        if daily_updates == "yes":
            if not email or not uploaded_file:
                flash("You must provide an email and upload a file for daily updates.", "danger")
                return redirect(url_for("search_input"))

            # Upload the file to Google Cloud Storage
            storage_client = storage.Client()
            bucket = storage_client.bucket(BUCKET_NAME)

            # Save the file to the bucket
            blob = bucket.blob(f"user_uploads/{session['username']}/{uploaded_file.filename}")
            blob.upload_from_file(uploaded_file)

            # Save the email and file location (in a separate data storage, like a CSV or database)
            save_user_data(email, blob.name)

            flash("You will now receive daily updates to your email.", "success")

        # Combine keywords from manual input and file
        file_keywords = []
        if uploaded_file:
            try:
                if uploaded_file.filename.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                elif uploaded_file.filename.endswith('.xlsx'):
                    df = pd.read_excel(uploaded_file)
                else:
                    flash("Unsupported file format. Please upload a CSV or Excel file.", "danger")
                    return redirect(url_for("search_input"))
                if 'keywords' not in df.columns:
                    flash("The uploaded file must contain a column named 'keywords'.", "danger")
                    return redirect(url_for("search_input"))
                file_keywords = df['keywords'].dropna().tolist()
            except Exception as e:
                flash("Error reading file. Please ensure it is a valid CSV or Excel file.", "danger")
                return redirect(url_for("search_input"))

        manual_keywords_list = [kw.strip() for kw in manual_keywords.split(",") if kw.strip()]
        all_keywords = list(set(file_keywords + manual_keywords_list))

        # Process the request as usual
        username = session["username"]
        process_request(email, all_keywords, username)
        flash("Search results have been sent to your email.", "success")
        return redirect(url_for("search_input"))

    return render_template("search.html")


# Route: Search Input
# @app.route("/search", methods=["GET", "POST"])
# def search_input():
#     if "username" not in session:
#         flash("Please log in first.", "warning")
#         return redirect(url_for("login"))

#     if request.method == "POST":
#         email = request.form["email"]
#         manual_keywords = request.form.get("manual_keywords", "").strip()
#         uploaded_file = request.files.get("keywords_file")

#         # Check if neither manual keywords nor a file was provided
#         if not manual_keywords and not uploaded_file:
#             flash("You must enter a keyword or upload a file to proceed.", "danger")
#             return redirect(url_for("search_input"))

#         # Extract keywords from uploaded file if provided
#         file_keywords = []
#         if uploaded_file:
#             try:
#                 if uploaded_file.filename.endswith('.csv'):
#                     df = pd.read_csv(uploaded_file)
#                 elif uploaded_file.filename.endswith('.xlsx'):
#                     df = pd.read_excel(uploaded_file)
#                 else:
#                     flash("Unsupported file format. Please upload a CSV or Excel file.", "danger")
#                     return redirect(url_for("search_input"))
#                 if 'keywords' not in df.columns:
#                     flash("The uploaded file must contain a column named 'keywords'.", "danger")
#                     return redirect(url_for("search_input"))
#                 file_keywords = df['keywords'].dropna().tolist()
#             except Exception as e:
#                 flash("Error reading file. Please ensure it is a valid CSV or Excel file.", "danger")
#                 return redirect(url_for("search_input"))

#         # Combine keywords from manual input and file
#         manual_keywords_list = [kw.strip() for kw in manual_keywords.split(",") if kw.strip()]
#         all_keywords = list(set(file_keywords + manual_keywords_list))
#         username = session["username"]

#         # Process the request
#         process_request(email, all_keywords, username)
#         flash("Search results have been sent to your email.", "success")
#         return redirect(url_for("search_input"))

    # return render_template("search.html")

from google.cloud import storage
import io
import pandas as pd

def save_user_data(email, file_location):
    storage_client = storage.Client()
    bucket = storage_client.bucket("tenders-excel-files")

    # Path to the user data CSV file in the bucket
    user_data_file_path = "user_info/user_data_info.csv"
    blob = bucket.blob(user_data_file_path)

    # Check if the file exists
    if blob.exists():
        # Read the existing CSV file without headers
        existing_data = blob.download_as_string()
        df = pd.read_csv(io.BytesIO(existing_data), header=None, names=['email', 'file_location'])
    else:
        # If the file doesn't exist, create a new DataFrame with headers
        df = pd.DataFrame(columns=['email', 'file_location'])

    # Append the new user data to the DataFrame
    new_data = pd.DataFrame({'email': [email], 'file_location': [file_location]})
    df = pd.concat([df, new_data], ignore_index=True)

    # Upload the updated DataFrame back to Google Cloud Storage as CSV
    with io.BytesIO() as output:
        df.to_csv(output, index=False, header=not blob.exists())
        output.seek(0)
        blob.upload_from_file(output, content_type='text/csv')
    
    print(f"User data saved: {email}, {file_location}")




# def save_user_data(email, file_location):
#     storage_client = storage.Client()
#     bucket = storage_client.bucket("tenders-excel-files")

#     # Path to the user data CSV file in the bucket
#     user_data_file_path = "user_info/user_data_info.csv"
#     blob = bucket.blob(user_data_file_path)
    
#     # Check if the file already exists
#     if not blob.exists():
#         # If it doesn't exist, create a new file and write the header
#         blob.upload_from_string('email,file_location\n')

#     # Prepare the data to append (email and file location)
#     user_data = f"{email},{file_location}\n"
    
#     # Append the user data to the file
#     blob.upload_from_string(user_data, if_generation_match=blob.generation)
#     print(f"User data saved: {email}, {file_location}")


def process_request(email, keywords, username):
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)

    all_matching_rows = []
    threshold = 80

    # Step 1: Download all the blobs (Excel files) once and process them
    blobs = list(bucket.list_blobs())
    all_files_data = {}

    # Download each file once and read into memory
    for blob in blobs:
        if blob.name.endswith(".xlsx"):
            print(f"Downloading {blob.name}...")
            blob_content = blob.download_as_string()  # Download file as string (no need to save it locally)
            df = pd.read_excel(BytesIO(blob_content))  # Read the content directly into a DataFrame
            all_files_data[blob.name] = df  # Store the DataFrame for later use

    # Step 2: For each keyword, perform fuzzy matching against all files
    for keyword in keywords:
        for file_name, df in all_files_data.items():
            if "subject" in df.columns:
                matches = df[df["subject"].apply(
                    lambda x: fuzz.partial_ratio(keyword.lower(), str(x).lower()) >= threshold
                )]
                if not matches.empty:
                    matches.insert(0, "keyword", keyword)
                    all_matching_rows.append(matches)

    # Step 3: Save and send email with the combined result
    if all_matching_rows:
        combined_df = pd.concat(all_matching_rows, ignore_index=True)
        result_file = f"tenders_combined_{today_date}_filtered_{username}.xlsx"

        print(f"Saving combined file: {result_file}")
        with pd.ExcelWriter(result_file, engine='xlsxwriter') as writer:
            combined_df.to_excel(writer, index=False)

        if combined_df.shape[0] > 0:
            send_email(
                to_addresses=[email],
                subject=f"Search Results for Keywords on {today_date}",
                body=f"Kindly find attached the extracted tender requests on {today_date} for the terms {keywords}.",
                attachments=[result_file]
            )

        if os.path.exists(result_file):
            print(f"Deleting file: {result_file}")
            os.remove(result_file)
    else:
        # If no matches are found for any keyword
        txt = ", ".join([f"'{val}'" for val in keywords])
        send_email(
            to_addresses=[email],
            subject=f"No Matches Found on {today_date}",
            body=f"No results were found for your query for {txt}.",
            attachments=None
        )

# Route: Logout
@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
