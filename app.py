from flask import Flask, request, render_template, redirect, url_for, session, flash
import pandas as pd
import os
from google.cloud import storage
from send_email import send_email
from dotenv import load_dotenv
from datetime import datetime
from fuzzywuzzy import fuzz
# Load environment variables
load_dotenv()

today_date = datetime.today().strftime('%Y-%m-%d')
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecret")

# Simulated user data for authentication
USER_DATA = {
    "omar": {"password": "123"}
}

# Google Cloud Storage configuration
BUCKET_NAME = "tenders-excel-files"

# Helper function to check credentials
def check_credentials(username, password):
    return username in USER_DATA and USER_DATA[username]["password"] == password

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

# Route: Search Input
@app.route("/search", methods=["GET", "POST"])
def search_input():
    if "username" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        email = request.form["email"]
        manual_keywords = request.form.get("manual_keywords", "").strip()
        uploaded_file = request.files.get("keywords_file")

        # Check if neither manual keywords nor a file was provided
        if not manual_keywords and not uploaded_file:
            flash("You must enter a keyword or upload a file to proceed.", "danger")
            return redirect(url_for("search_input"))

        # Extract keywords from uploaded file if provided
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

        # Combine keywords from manual input and file
        manual_keywords_list = [kw.strip() for kw in manual_keywords.split(",") if kw.strip()]
        all_keywords = list(set(file_keywords + manual_keywords_list))
        username = session["username"]

        # Process the request
        process_request(email, all_keywords, username)
        flash("Search results have been sent to your email.", "success")
        return redirect(url_for("search_input"))

    return render_template("search.html")

def process_request(email, keywords, username):
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)

    all_matching_rows = []
    threshold=80

    for keyword in keywords:
        blobs = bucket.list_blobs()

        for blob in blobs:
            if blob.name.endswith(".xlsx"):
                blob.download_to_filename("temp.xlsx")
                df = pd.read_excel("temp.xlsx")
                if "subject" in df.columns:
                    matches = df[df["subject"].apply(
                        lambda x: fuzz.partial_ratio(keyword.lower(), str(x).lower()) >= threshold
                    )]
                    if not matches.empty:
                        matches.insert(0, "keyword", keyword)
                        all_matching_rows.append(matches)
                os.remove("temp.xlsx")

    if all_matching_rows:
        # Combine all matching rows into a single DataFrame
        combined_df = pd.concat(all_matching_rows, ignore_index=True)
        result_file = f"tenders_combined_{today_date}_filtered_{username}.xlsx"

        # Save the combined DataFrame to a single file
        print(f"Saving combined file: {result_file}")
        with pd.ExcelWriter(result_file, engine='xlsxwriter') as writer:
            combined_df.to_excel(writer, index=False)
        # Send a single email with the combined file
        if combined_df.shape[0]>0:
            send_email(
                to_addresses=[email],
                subject=f"Search Results for Keywords on {today_date}",
                body=f"Kindly find attached the extracted tender requests on {today_date} for the terms {keywords}.",
                attachments=[result_file]
            )

        # Clean up the local file after sending the email
            if os.path.exists(result_file):
                print(f"Deleting file: {result_file}")
                os.remove(result_file)
    else:
        # If no matches are found for any keyword
        txt=""
        for val in keywords:
            txt+=f"'{val},'"
        send_email(
                to_addresses=[email],
                subject=f"No Matches Found on {today_date}",
                body=f"No results were found for your query for {txt}.",
                attachments=None
            )



# V2//multiple emails for more than 2 files
# def process_request(email, keywords, username):
#     storage_client = storage.Client()
#     bucket = storage_client.bucket(BUCKET_NAME)

#     for keyword in keywords:
#         blobs = bucket.list_blobs()
#         matching_rows = []

#         for blob in blobs:
#             if blob.name.endswith(".xlsx"):
#                 blob.download_to_filename("temp.xlsx")
#                 df = pd.read_excel("temp.xlsx")
#                 if "subject" in df.columns:
#                     matches = df[df["subject"].str.contains(keyword, na=False, case=False)]
#                     matching_rows.append(matches)
#                 os.remove("temp.xlsx")

#         if matching_rows:
#             result_df = pd.concat(matching_rows, ignore_index=True)
#             result_file = f"tenders_{today_date}_filtered_{username}.xlsx"
#             result_df.to_excel(result_file, index=False)
#             send_email(
#                 to_addresses=[email],
#                 subject=f"Search Results for {keyword}",
#                 body=f"Kindly find attached the extracted tender requests for {today_date} :)",
#                 username=username
#             )
#             os.remove(result_file)
#         else:
#             send_email(
#                 to_addresses=[email],
#                 subject=f"No Matches Found for {keyword}",
#                 body="No results were found for your query.",
#                 username=username
#             )




# Helper Function: Process Request
# def process_request(email, keywords):
#     storage_client = storage.Client()
#     bucket = storage_client.bucket(BUCKET_NAME)

#     for keyword in keywords:
#         blobs = bucket.list_blobs()
#         matching_rows = []

#         for blob in blobs:
#             if blob.name.endswith(".xlsx"):
#                 blob.download_to_filename("temp.xlsx")
#                 df = pd.read_excel("temp.xlsx")
#                 if "subject" in df.columns:
#                     matches = df[df["subject"].str.contains(keyword, na=False, case=False)]
#                     matching_rows.append(matches)
#                 os.remove("temp.xlsx")

#         if matching_rows:
#             result_df = pd.concat(matching_rows, ignore_index=True)
#             result_file = f"results_{keyword}.xlsx"
#             result_df.to_excel(result_file, index=False)
#             send_email([email], f"Search Results for {keyword}", "Please find the attached results.", attachments=[result_file])
#             os.remove(result_file)
#         else:
#             send_email([email], f"No Matches Found for {keyword}", "No results were found for your query.")

# Route: Logout
@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
