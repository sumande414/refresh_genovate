from flask import Flask, jsonify
import pymysql
from imap_tools import MailBox, AND
from dotenv import load_dotenv
import os


load_dotenv()

app = Flask(__name__)


IMAP_SERVER = os.getenv("IMAP_SERVER")
EMAIL_ACCOUNT = os.getenv("EMAIL_ACCOUNT")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = int(os.getenv("DB_PORT"))

def save_email_to_db(subject, sender, recipient, cc, bcc, email_date, body):
    try:
        timeout = 10
        conn = pymysql.connect(
            charset="utf8mb4",
            connect_timeout=timeout,
            cursorclass=pymysql.cursors.DictCursor,
            db=DB_NAME,
            host=DB_HOST,
            password=DB_PASSWORD,
            read_timeout=timeout,
            port=DB_PORT,
            user=DB_USER,
            write_timeout=timeout,
        )
        cursor = conn.cursor()

        query = """
        INSERT INTO RawEmails (subject, sender, recipient, cc, bcc, email_date, body)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        values = (subject, sender, recipient, cc, bcc, email_date, body)

        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()

        print(f"Saved email: {subject}")

    except pymysql.MySQLError as err:
        print(f"MySQL Error: {err}")

@app.route('/refresh', methods=['GET'])
def fetch_and_store_emails():
    try:
        with MailBox(IMAP_SERVER).login(EMAIL_ACCOUNT, EMAIL_PASSWORD, initial_folder="INBOX") as mailbox:
            unread_emails = []
            for msg in mailbox.fetch(AND(seen=False)): 
                save_email_to_db(
                    subject=msg.subject,
                    sender=msg.from_,
                    recipient=", ".join(msg.to) if msg.to else "",
                    cc=", ".join(msg.cc) if msg.cc else "",
                    bcc=", ".join(msg.bcc) if msg.bcc else "",
                    email_date=msg.date.strftime("%Y-%m-%d %H:%M:%S"),
                    body=msg.text or msg.html
                )
                mailbox.flag(msg.uid, [r'\Seen'], True)
                unread_emails.append(msg.subject)

            response = jsonify({"message": "Emails fetched and stored successfully", "emails": unread_emails})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response,200

    except Exception as e:
        print(f"Error: {e}")
        response = jsonify({"message": "An error occurred while fetching emails", "error": str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response,500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
