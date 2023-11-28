print("Initialization ongoing, wait for some seconds...")

import cv2
import face_recognition
import os
import signal
import smtplib
import imghdr
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import date
from email.message import EmailMessage
import RPi.GPIO as GPIO
from RPLCD import CharLCD
import time
from flask import Flask, render_template, request, session
import threading

text = "INITIALIZATION ONGOING, PLEASE WAIT FOR SOME SECONDS..."
os.system("espeak -ven+m7 -k5 -s120 -a 200 -g3 '{}'".format(text))

GPIO.setmode(GPIO.BCM)    # Consider complete raspberry-pi board
GPIO.setwarnings(False)     # To avoid same PIN use warning

# Define GPIO to LCD mapping
lcd = CharLCD(numbering_mode=GPIO.BCM, cols=16, rows=2, pin_rs=7, pin_e=8, pins_data=[25, 24, 23, 18])
lcd.clear()
lcd.write_string(u'Please Wait for\n\rsome seconds...')

# Define GPIO
motor_pin1 = 14


GPIO.setup(motor_pin1, GPIO.OUT)
servo = GPIO.PWM(motor_pin1, 50)
 

CurrentFolder = os.getcwd() #Read current folder path
image = CurrentFolder+'/Bolu.jpg'
image2 = CurrentFolder+'/Gift.jpg'

# Load a sample picture and encode it.
person1_name = "Bolu"
person1_image = face_recognition.load_image_file(image)
person1_face_locations = face_recognition.face_locations(person1_image)
person1_face_encodings = face_recognition.face_encodings(person1_image, person1_face_locations)

# Should incase a face is not found
if len(person1_face_encodings) > 0:
    person1_face_encoding = face_recognition.face_encodings(person1_image)[0]
    # Continue with further processing using face_encoding
else:
    print("No face found in the image.")

# Load the Seecond face image and encode it
person2_name = "Gift"
person2_image = face_recognition.load_image_file(image2)
person2_face_locations = face_recognition.face_locations(person2_image)
person2_face_encodings = face_recognition.face_encodings(person2_image, person2_face_locations)

# Should incase a face is not found
if len(person2_face_encodings) > 0:
    person2_face_encoding = face_recognition.face_encodings(person2_image)[0]
    # Continue with further processing using face_encoding
else:
    print("No face found in the image.")

# Create arrays of known face encodings and their names
known_face_encodings = [
    person1_face_encoding,
    person2_face_encoding
]

known_face_names = [
    person1_name,
    person2_name
]

# Initialize some variables
face_locations = []
face_encodings = []
face_names = []
uploaded_file_url = None

# Initialize the video capture
video_capture = cv2.VideoCapture(0)

# Create a lock to synchronize access to the access_granted flag
access_lock = threading.Lock()

row=3
row2=3
col=1
awaiting_confirmation = False
already_attendance_taken = None 

# Create access to Google sheet
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CurrentFolder+"/creds.json", scope)
client = gspread.authorize(creds)

sheet = client.open("visitor_record_excel").sheet1
sheet2 = client.open("attendance_excel").get_worksheet(1)

lcd.clear()
lcd.write_string(u'Welcome!')
text = "WELCOME"
os.system("espeak -ven+m7 -k5 -s120 -a 200 -g3 '{}'".format(text))
time.sleep(3)
lcd.clear() # Clear display
lcd.write_string(u'Visitor Mgmt\n\rSystem')
text = "How are you doing today?"
os.system("espeak -ven+m7 -k5 -s120 -a 200 -g3 '{}'".format(text))
time.sleep(3)

servo.start(2) #DOOR CLOSED

def facial_recognition_loop():
    global awaiting_confirmation, row, row2, col, already_attendance_taken
        
    lcd.clear() # Clear display
    lcd.write_string(u'Hi, Please Face\n\rthe camera')
    text = "PLEASE FACE THE CAMERA"
    os.system("espeak -ven+m7 -k5 -s120 -a 200 -g3 '{}'".format(text))
    time.sleep(1)
    while True:
        # Grab a single frame of video
        ret, frame = video_capture.read()
        
        current_face_encoding = None

        # Only process every other frame of video to save time
        if current_face_encoding is None and not awaiting_confirmation:
            # Find all the faces and their encodings in the frame
            face_locations = face_recognition.face_locations(frame)
            face_encodings = face_recognition.face_encodings(frame, face_locations)

            # Create an empty list to store every detected face
            face_names = []

            # Iterate over the detected faces in the frame
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                # Compare the face encoding with the known face encodings
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            
                # Find the best match face with the minimum distance
                best_match_index = face_distances.argmin()
                if matches[best_match_index]:
                    # Recognized face
                    print("Face recognized!")
                    lcd.clear() # Clear display
                    lcd.write_string(u'Face recognized!')
                    current_face_encoding = face_encoding
                    text = "FACE RECOGNIZED"
                    os.system("espeak -ven+m7 -k5 -s120 -a 200 -g3 '{}'".format(text))
                    name = known_face_names[best_match_index]
                    face_names.append(name)
                    print(name, 'Identified')
                    time.sleep(3)
                else:
                    name = "Unknown"
                    print("Unknown!")
                    current_face_encoding = None
                    lcd.clear() # Clear display
                    lcd.write_string(u'Unknown!')
                    text = "SORRY, I DO NOT KNOW YOU"
                    os.system("espeak -ven+m7 -k5 -s120 -a 200 -g3 '{}'".format(text))
                    time.sleep(3)
                        
                if (name == "Unknown"):
                    lcd.clear() # Clear display
                    lcd.write_string(u'Kindly Enter\n\ryour Name_')
                    text = "PLEASE ENTER YOUR NAME"
                    os.system("espeak -ven+m7 -k5 -s120 -a 200 -g3 '{}'".format(text))
                    inp = input('Enter your name: ')
                    time.sleep(1)
                    name = inp
                    print("sending image to mail")
                    text = "PLEASE AWAIT CONFIRMATION..."
                    os.system("espeak -ven+m7 -k5 -s120 -a 200 -g3 '{}'".format(text))
                    lcd.clear() # Clear display
                    lcd.write_string(u'Sending image to\n\rmail...')
                    #return_value, image = video_capture.read()
                    cv2.imwrite('visitor.png', frame)
                    Sender_Email = "**********@gmail.com"
                    Reciever_Email = "**********@gmail.com"
                    Password = "*************" #type your password here
                    newMessage = EmailMessage()                         
                    newMessage['Subject'] = "Visitor Image" 
                    newMessage['From'] = Sender_Email                   
                    newMessage['To'] = Reciever_Email
                    email_content = f"Let me know what you think. Image attached! and name is: {name}\nVisit <ip address of raspberrypi>/ to grant access."
                    newMessage.set_content(email_content) 
                    with open('visitor.png', 'rb') as f:
                        image_data = f.read()
                        image_type = imghdr.what(f.name)
                        image_name = f.name
                    newMessage.add_attachment(image_data, maintype='image', subtype=image_type, filename=image_name)
                    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                        smtp.login(Sender_Email, Password)              
                        smtp.send_message(newMessage)
                                
                    lcd.clear() # Clear display
                    lcd.write_string(u'Awaiting\n\rconfirmation...')
                            
                    # Create the Google Drive service
                    credentials = CurrentFolder+'/client_secrets.json'
                    service = build('drive', 'v3', credentials=creds)

                    # Upload the file to Google Drive
                    folder_id = '1YaY44LfbhiemvRXTN76qIjmrNYECqZB9'  # Replace with the ID of the folder you want to upload the image to
                    file_name = 'visitor.png'
                    file_metadata = {
                        'name': file_name,
                        'parents': [folder_id],
                    }
                    media = MediaFileUpload('visitor.png', mimetype='image/png')
                    uploaded_file = service.files().create(body=file_metadata, media_body=media, fields='id,webContentLink').execute()
                    print("Upload complete!")

                    # Get the URL of the uploaded image
                    uploaded_file_url = uploaded_file['webContentLink']

                    # Update  Database
                    sheet.update_cell(row2,col, name)
                    col = col+1
                    sheet.update_cell(row2,col, str(date.today()))
                    col = col+1
                    sheet.update_cell(row2,col, str(time.strftime("%H:%M:%S", time.localtime())))
                    col = col+1
                    if uploaded_file_url is not None:
                        sheet.update_cell(row2, col, f'=HYPERLINK("{uploaded_file_url}", "Link")')
                    row2 = row2 + 1
                    col = 1
                    awaiting_confirmation = True
                    

                else:
                    lcd.clear() # Clear display
                    lcd.write_string(u"Welcome "+ name)
                    text = f"WELCOME {name}"
                    os.system("espeak -ven+m7 -k5 -s120 -a 200 -g3 '{}'".format(text))
                    servo.ChangeDutyCycle(7)
                    time.sleep(3)
                    servo.ChangeDutyCycle(2)
                    time.sleep(1)
                    #Update attendance
                    sheet2.update_cell(row,col, name)
                    col = col+1
                    sheet2.update_cell(row,col, str(date.today()))
                    col = col+1
                    sheet2.update_cell(row,col, str(time.strftime("%H:%M:%S", time.localtime())))
                    col = col+1
                    sheet2.update_cell(row, col, 'Present')
                    row = row + 1
                    col = 1
                    already_attendence_taken = name

        # Display the results
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            # Scale back up face locations since the frame we detected in was scaled to 1/4 size
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            # Draw a box around the face
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

            # Draw a label with a name below the face
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)
        
        # Display the resulting image
        cv2.imshow('Video', frame)
        if (cv2.waitKey(2) == 27):
            cv2.destroyAllWindows()
            break

def signal_handler(sig, frame):
    global video_capture
    print("\nStopping the application...")
    video_capture.release()
    cv2.destroyAllWindows()
    servo.stop()
    GPIO.cleanup()
    print("Application stopped.")
    exit(0)

def stop_facial_recognition():
    global facial_recognition_process
    facial_recognition_process.join()
    facial_recognition_process = threading.Thread(target=facial_recognition_loop)

app = Flask(__name__)
app.secret_key = "your_secret_key_here"


# Set a flag to indicate if access has been granted
access_granted = False

@app.before_request
def clear_access_granted():
    session['access_granted'] = False

@app.route('/')
def index():
    global access_granted

    # If access has been granted, return the access message
    if session.get('access_granted'):
        return "Access granted!"

    return render_template('index.html')

# Set LCD messages for access status
ACCESS_GRANTED_MSG = "Access granted"
ACCESS_DENIED_MSG = "Access denied,\n\rkindly leave"

@app.route('/access_control')
def access_control():
    global access_granted, current_face_encoding, awaiting_confirmation

    # Get the action from the request parameters
    action = request.args.get('action', '').lower()

    # Handle the access control based on the action
    if action == 'grant':
        if awaiting_confirmation is True:
            print("Opening the door...")
            lcd.clear()
            lcd.write_string(ACCESS_GRANTED_MSG)
            text = "ACCESS GRANTED!"
            os.system("espeak -ven+m7 -k5 -s120 -a 200 -g3 '{}'".format(text))
            servo.ChangeDutyCycle(7.5)
            time.sleep(3)
            servo.ChangeDutyCycle(2)
            time.sleep(1)
            lcd.clear() # Clear display
            lcd.write_string(u'Hi, Please Face\n\rthe camera')
            text = "PLEASE FACE THE CAMERA"
            os.system("espeak -ven+m7 -k5 -s120 -a 200 -g3 '{}'".format(text))
            current_face_encoding = None
            awaiting_confirmation = False
            session['access_granted'] = True
            return "Access granted!"
        else:
            return "No recognized face to grant access to."
    elif action == 'deny':
        if awaiting_confirmation is True:
            print("Access denied!")
            lcd.clear()
            lcd.write_string(ACCESS_DENIED_MSG)
            text = "ACCESS DENIED!"
            os.system("espeak -ven+m7 -k5 -s120 -a 200 -g3 '{}'".format(text))
            servo.ChangeDutyCycle(2)
            time.sleep(3)
            lcd.clear() # Clear display
            lcd.write_string(u'Hi, Please Face\n\rthe camera')
            text = "PLEASE FACE THE CAMERA"
            os.system("espeak -ven+m7 -k5 -s120 -a 200 -g3 '{}'".format(text))
            current_face_encoding = None
            awaiting_confirmation = False
            session['access_granted'] = False
            return "Access denied, kindly leave"
        else:
            return "No recognized face to deny access to."
    else:
        return "Invalid action"



if __name__ == '__main__':
    # Register the signal handler to catch the termination signal (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)

    # Create and start the facial recognition process
    facial_recognition_process = threading.Thread(target=facial_recognition_loop)
    facial_recognition_process.start()
    
     # Run the Flask app in another thread
    app_thread = threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 5000, 'threaded': True})
    app_thread.start()
