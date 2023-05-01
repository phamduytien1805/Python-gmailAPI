from __future__ import print_function
from flask import Flask
from flask import request
import json
import base64
import mimetypes
import datetime

import os.path
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

app = Flask(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://mail.google.com/']

remoteGmail = 'tuannguyen221pro@gmail.com'
# credentials of app
creds = None


def beginWatchMailBox():
    try:
        global creds
        print(creds)
        service = build('gmail', 'v1', credentials=creds)
        request = {
            "labelIds": ["INBOX"],
            "topicName": "projects/test-gmail-382511/topics/gmail-watc",
            "labelFilterAction": "include",
        }
        response = service.users().watch(userId="me", body=request).execute()
        print(response)

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}')


def authorize():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    global creds
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())


def getListEmail():
    global creds
    service = build('gmail', 'v1', credentials=creds)
    msgResponse = service.users().messages().list(userId="me", q=f"from: {remoteGmail} is:unread").execute()
    print('msgResponse', msgResponse)
    if "messages" in msgResponse:
        msgList = msgResponse["messages"]

        # print('msgResponse',msgResponse["messages"])
        if len(msgList):
            newestMsg = msgList[-1]
            msgResponse = service.users().messages().get(userId="me", id=newestMsg['id']).execute()
            payload = msgResponse['payload']

            base64PlainMsg = payload['parts'][0]['body']['data']
            rawMsg = base64.b64decode(base64PlainMsg).decode('utf-8')
            print(f"Content of m: {rawMsg} AAAA")
            if rawMsg:
                # read the message
                modifyMessage = {
                    "removeLabelIds": ["UNREAD"],
                }
                service.users().messages().modify(userId="me", id=newestMsg['id'], body=modifyMessage).execute()
                replyMsg = createMessage(newestMsg['id'], newestMsg['threadId'], payload['headers'], 'this is content')
                replyMsg_attachments = createMessageWithAttachments(newestMsg['id'], newestMsg['threadId'],payload['headers'], 'this is content', rawMsg[:-2])

                # sent = gmail_send_message(replyMsg)
                sent_attachments = gmail_send_message(replyMsg_attachments)
                print('sent', sent_attachments)
                # TODO: Lấy rawMsg, threadID để thực hiện các bước khác nha


def createMessage(messagesId, threadId, headers, content):
    try:
        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']
            elif header['name'] == 'From':
                sender = header['value']
        print('subject', subject)
        replyMsg = EmailMessage()
        replyMsg.set_content(content)
        replyMsg['To'] = sender
        replyMsg['Subject'] = 'Re: ' + subject
        replyMsg.add_header('In-Reply-To', messagesId)
        replyMsg.add_header('References', threadId)

        # encoded message
        encoded_message = base64.urlsafe_b64encode(replyMsg.as_bytes()).decode()
        create_message = {
            'raw': encoded_message,
            'threadId': threadId
        }
    except:
        create_message = None
        print(F'An error occurred')
    return create_message


def createMessageWithAttachments(messagesId, threadId, headers, content, attachments_type):
    try:
        # create gmail api client
        mime_message = EmailMessage()

        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']
            elif header['name'] == 'From':
                sender = header['value']

        # headers
        mime_message['To'] = sender
        mime_message['Subject'] = f'Re: {subject}'

        # text
        mime_message.set_content(
            content
        )

        # attachment

        attachment_filename = createa_attachment(attachments_type)
        # attachment_filename = capture_screen()
        # print(attachment_filename)
        # guessing the MIME type
        type_subtype, _ = mimetypes.guess_type(attachment_filename)
        maintype, subtype = type_subtype.split('/')
        print('type_subtype', type_subtype)

        with open(attachment_filename, 'rb') as fp:
            attachment_data = fp.read()
        mime_message.add_attachment(attachment_data, maintype, subtype)

        encoded_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()

        createMessage = {
            'raw': encoded_message
        }
    except HttpError as error:
        print(F'An error occurred: {error}')
        createMessage = None
    return createMessage

def gmail_send_message(create_message):
    global creds
    try:
        service = build('gmail', 'v1', credentials=creds)
        send_message = (service.users().messages().send(userId="me", body=create_message).execute())
        print(F'Message Id: {send_message["id"]}')
    except HttpError as error:
        print(F'An error occurred: {error}')
        send_message = None
    return send_message

def createa_attachment(attachments_type):
    print('Creating attachment')
    match attachments_type:
        case "get list process":
            return getListProcess()
        case "capture screen":
            return capture_screen()

        case "get list application":
            return get_list_app()
        case default:
            return "something"


def capture_screen():
    from PIL import ImageGrab
    # Capture the screen
    image = ImageGrab.grab()
    # Save the image
    file_name = f"screenshot_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
    image.save(file_name)

    return file_name


def getListProcess():
    import psutil
    # Get list of running processes with ID and status
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'status']):
        processes.append(proc.info)
    file_name = f"process_list_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
    # Write list of processes with ID and status to a text file
    with open(file_name, 'w') as f:
        for proc in processes:
            f.write(f"PID: {proc['pid']}, Name: {proc['name']}, Status: {proc['status']}\n")

    return file_name


def get_list_app():
    import winreg
    # Open the registry key for installed applications
    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
    # Create a new file to write the list to
    file_name = f"installed_apps{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
    with open(file_name, "w") as f:
        # Iterate over the subkeys of the installed applications key
        for i in range(winreg.QueryInfoKey(key)[0]):
            try:
                # Get the subkey name and open it
                subkey_name = winreg.EnumKey(key, i)
                subkey = winreg.OpenKey(key, subkey_name)

                # Get the display name and publisher values
                display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                publisher = winreg.QueryValueEx(subkey, "Publisher")[0]

                # Write the display name and publisher to the file
                f.write(f"{display_name} - {publisher}\n")

            except WindowsError:
                # Ignore any subkeys that cannot be opened or do not have a display name
                pass
    # Close the registry key
    winreg.CloseKey(key)
    return file_name

def main():
    authorize()
    beginWatchMailBox()

@app.route('/push', methods=['POST'])
def receiveGmailNotification():
    try:
        if request.method == 'POST':
            # data = request.get_json()
            getListEmail()
            return {}, 200
        return {}, 200
    except HttpError as error:
        print(f'An error occurred: {error}')
        return {}, 200

if __name__ == '__main__':
    main()
    app.run(host='localhost', port=3333)
