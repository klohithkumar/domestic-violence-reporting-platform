from flask import Flask,render_template,request,flash,redirect,url_for,session,send_from_directory,send_file
from werkzeug.security import generate_password_hash,check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
import os
import random
import string
import smtplib
import secrets
import time
from email.message import EmailMessage
import joblib
import numpy as np

app=Flask(__name__)
app.secret_key="safevoice123"
AI_MODEL=joblib.load("ai/violence_classifier.pkl")
AI_VECTORIZER=joblib.load("ai/tfidf_vectorizer.pkl")
VIOLENCE_TYPES=[
    "Physical Violence",
    "Emotional / Psychological Violence",
    "Economic Violence",
    "Sexual Violence",
    "Controlling Behaviour"
]
print("SafeVoice AI model loaded successfully.")
MAIL_ADDRESS="safevoice.admin@gmail.com"
MAIL_PASSWORD="rhjy vocg bwcc vaom"
app.config["SESSION_PERMANENT"]=False
UPLOAD_FOLDER="uploads"
ALLOWED_EXTENSIONS={"jpg","jpeg","png","pdf","mp4"}
app.config["UPLOAD_FOLDER"]=UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"]=50*1024*1024
os.makedirs(UPLOAD_FOLDER,exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS

def analyze_report(description):
    try:
        text=AI_VECTORIZER.transform([description])
        predictions=AI_MODEL.predict(text)[0]
        results={}
        for i,violence_type in enumerate(VIOLENCE_TYPES):
            results[violence_type]=int(predictions[i])
        return results
    except Exception as e:
        print("AI ANALYSIS ERROR:",e)
        return {violence_type:0 for violence_type in VIOLENCE_TYPES}

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        fullname=request.form["fullname"].strip()
        email=request.form["email"].strip().lower()
        country_code=request.form["country_code"]
        phone=request.form["phone"].strip()
        password=request.form["password"]
        confirm_password=request.form["confirm_password"]
        entered_captcha=request.form["captcha"].strip().upper()
        stored_captcha=session.get("captcha")
        if entered_captcha!=stored_captcha:
            flash("Invalid CAPTCHA. Please try again.","error")
            return redirect(url_for("register"))
        if not fullname or not fullname.replace(" ","").isalpha():
            flash("Please enter a valid full name.","error")
            return redirect(url_for("register"))
        if "@" not in email or "." not in email.split("@")[-1]:
            flash("Please enter a valid email address.","error")
            return redirect(url_for("register"))
        if not phone.isdigit() or len(phone)<7 or len(phone)>15:
            flash("Please enter a valid phone number.","error")
            return redirect(url_for("register"))
        if len(password)<8 or not any(c.isupper() for c in password) or not any(c.islower() for c in password) or not any(c.isdigit() for c in password) or not any(not c.isalnum() for c in password):
            flash("Password must contain 8+ characters, uppercase, lowercase, number and special character.","error")
            return redirect(url_for("register"))
        if password!=confirm_password:
            flash("Passwords do not match.","error")
            return redirect(url_for("register"))
        conn=sqlite3.connect("database.db")
        cursor=conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?",(email,))
        user=cursor.fetchone()
        conn.close()
        if user:
            flash("Email already registered. Please login.","error")
            return redirect(url_for("login"))
        otp=str(secrets.randbelow(900000)+100000)
        session["pending_registration"]={
            "fullname":fullname,
            "email":email,
            "phone":country_code+phone,
            "password":generate_password_hash(password),
            "otp":otp,
            "otp_time":time.time()
        }
        try:
            message=EmailMessage()
            message["Subject"]="SafeVoice Email Verification"
            message["From"]=MAIL_ADDRESS
            message["To"]=email
            message.set_content(f"Your SafeVoice verification code is: {otp}\n\nThis code is valid for 5 minutes.\n\nIf you did not create a SafeVoice account, please ignore this email.")
            with smtplib.SMTP_SSL("smtp.gmail.com",465) as server:
                server.login(MAIL_ADDRESS,MAIL_PASSWORD)
                server.send_message(message)
        except Exception as e:
            session.pop("pending_registration",None)
            print("GMAIL ERROR:",e)
            flash("Unable to send verification email. Please try again.","error")
            return redirect(url_for("register"))
        session.pop("captcha",None)
        return redirect(url_for("verify_otp"))
    captcha="".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
    session["captcha"]=captcha
    return render_template("register.html",captcha=captcha)

@app.route("/verify_otp",methods=["GET","POST"])
def verify_otp():
    pending=session.get("pending_registration")
    if not pending:
        return redirect(url_for("register"))
    if request.method=="POST":
        entered_otp=request.form["otp"].strip()
        if time.time()-pending["otp_time"]>300:
            session.pop("pending_registration",None)
            flash("OTP expired. Please register again.","error")
            return redirect(url_for("register"))
        if entered_otp!=pending["otp"]:
            flash("Invalid verification code. Please try again.","error")
            return redirect(url_for("verify_otp"))
        conn=sqlite3.connect("database.db")
        cursor=conn.cursor()
        cursor.execute("INSERT INTO users(fullname,email,password,phone) VALUES(?,?,?,?)",(pending["fullname"],pending["email"],pending["password"],pending["phone"]))
        conn.commit()
        conn.close()
        session.pop("pending_registration",None)
        session["user"]=pending["fullname"]
        session["email"]=pending["email"]
        flash("Registration successful! Welcome to SafeVoice.","success")
        return redirect(url_for("dashboard"))
    return render_template("verify_otp.html")

@app.route("/login",methods=["GET","POST"])
def login():
    captcha_chars=string.ascii_letters+string.digits
    if request.method=="GET":
        session["login_captcha"]="".join(random.choices(captcha_chars,k=6))
    if request.method=="POST":
        email=request.form["email"].strip().lower()
        password=request.form["password"]
        captcha=request.form["captcha"].strip()
        if captcha!=session.get("login_captcha"):
            flash("Invalid CAPTCHA!","error")
            session["login_captcha"]="".join(random.choices(captcha_chars,k=6))
            return redirect(url_for("login"))
        conn=sqlite3.connect("database.db")
        cursor=conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?",(email,))
        user=cursor.fetchone()
        conn.close()
        if user and check_password_hash(user[3],password):
            session.pop("login_captcha",None)
            session["user"]=user[1]
            session["email"]=user[2]
            return redirect(url_for("dashboard"))
        flash("Invalid Email or Password!","error")
        session["login_captcha"]="".join(random.choices(captcha_chars,k=6))
        return redirect(url_for("login"))
    return render_template("login.html",captcha=session.get("login_captcha"))

@app.route("/forgot_password",methods=["GET","POST"])
def forgot_password():
    if request.method=="POST":
        email=request.form["email"].strip().lower()
        conn=sqlite3.connect("database.db")
        cursor=conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?",(email,))
        user=cursor.fetchone()
        conn.close()
        if not user:
            flash("No account found with this email address.","error")
            return redirect(url_for("forgot_password"))
        otp=str(secrets.randbelow(900000)+100000)
        session["password_reset"]={
            "email":email,
            "otp":otp,
            "otp_time":time.time()
        }
        try:
            message=EmailMessage()
            message["Subject"]="SafeVoice Password Reset"
            message["From"]=MAIL_ADDRESS
            message["To"]=email
            message.set_content(f"Your SafeVoice password reset code is: {otp}\n\nThis code is valid for 5 minutes.\n\nIf you did not request a password reset, please ignore this email.")
            with smtplib.SMTP_SSL("smtp.gmail.com",465) as server:
                server.login(MAIL_ADDRESS,MAIL_PASSWORD)
                server.send_message(message)
        except Exception as e:
            session.pop("password_reset",None)
            print("GMAIL ERROR:",e)
            flash("Unable to send verification email. Please try again.","error")
            return redirect(url_for("forgot_password"))
        flash("Verification code sent to your email.","success")
        return redirect(url_for("reset_otp"))
    return render_template("forgot_password.html")


@app.route("/reset_otp",methods=["GET","POST"])
def reset_otp():
    reset=session.get("password_reset")
    if not reset:
        return redirect(url_for("forgot_password"))
    if request.method=="POST":
        entered_otp=request.form["otp"].strip()
        if time.time()-reset["otp_time"]>300:
            session.pop("password_reset",None)
            flash("OTP expired. Please try again.","error")
            return redirect(url_for("forgot_password"))
        if entered_otp!=reset["otp"]:
            flash("Invalid verification code.","error")
            return redirect(url_for("reset_otp"))
        session["reset_verified"]=True
        return redirect(url_for("new_password"))
    return render_template("reset_otp.html")


@app.route("/new_password",methods=["GET","POST"])
def new_password():
    reset=session.get("password_reset")
    if not reset or not session.get("reset_verified"):
        return redirect(url_for("forgot_password"))
    if request.method=="POST":
        password=request.form["password"]
        confirm_password=request.form["confirm_password"]
        if len(password)<8 or not any(c.isupper() for c in password) or not any(c.islower() for c in password) or not any(c.isdigit() for c in password) or not any(not c.isalnum() for c in password):
            flash("Password must contain 8+ characters, uppercase, lowercase, number and special character.","error")
            return redirect(url_for("new_password"))
        if password!=confirm_password:
            flash("Passwords do not match.","error")
            return redirect(url_for("new_password"))
        conn=sqlite3.connect("database.db")
        cursor=conn.cursor()
        cursor.execute("UPDATE users SET password=? WHERE email=?",(generate_password_hash(password),reset["email"]))
        conn.commit()
        conn.close()
        session.pop("password_reset",None)
        session.pop("reset_verified",None)
        flash("Password reset successfully. Please login.","success")
        return redirect(url_for("login"))
    return render_template("new_password.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html",name=session["user"])

@app.route("/report",methods=["GET","POST"])
def report():
    if "user" not in session:
        return redirect(url_for("login"))
    if request.method=="POST":
        fullname=request.form["fullname"]
        phone=request.form["phone"]
        location=request.form["location"]
        incident_date=request.form["incident_date"]
        description=request.form["description"]
        file=request.files.get("evidence")
        filename=""
        if file and file.filename:
            if not allowed_file(file.filename):
                flash("Invalid file type! Allowed: JPG, JPEG, PNG, PDF, MP4.","error")
                return redirect(url_for("report"))
            filename=secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"],filename))
        ai_results=analyze_report(description)
        ai_analysis=", ".join([violence_type for violence_type,detected in ai_results.items() if detected==1])
        if not ai_analysis:
            ai_analysis="No violence category detected"
        conn=sqlite3.connect("database.db")
        cursor=conn.cursor()
        cursor.execute("""
            INSERT INTO reports
            (fullname,email,phone,location,incident_date,description,status,evidence,ai_analysis)
            VALUES (?,?,?,?,?,?,?,?,?)
        """,(fullname,session["email"],phone,location,incident_date,description,"Pending",filename,ai_analysis))
        conn.commit()
        conn.close()
        flash("Report submitted successfully and analyzed by SafeVoice AI!","success")
        return redirect(url_for("myreports"))
    return render_template("report.html")

@app.route("/myreports")
def myreports():
    if "user" not in session:
        return redirect(url_for("login"))
    conn=sqlite3.connect("database.db")
    cursor=conn.cursor()
    cursor.execute("SELECT id,fullname,phone,location,incident_date,description,status,ai_analysis FROM reports WHERE email=?",(session["email"],))
    reports=cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM reports WHERE email=?",(session["email"],))
    total_reports=cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM reports WHERE email=? AND status='Pending'",(session["email"],))
    pending=cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM reports WHERE email=? AND status='Reviewed'",(session["email"],))
    reviewed=cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM reports WHERE email=? AND status='Resolved'",(session["email"],))
    resolved=cursor.fetchone()[0]
    conn.close()
    return render_template("myreports.html",reports=reports,total_reports=total_reports,pending=pending,reviewed=reviewed,resolved=resolved)

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully!","success")
    response=redirect(url_for("login"))
    response.headers["Cache-Control"]="no-cache,no-store,must-revalidate"
    response.headers["Pragma"]="no-cache"
    response.headers["Expires"]="0"
    return response

@app.route("/admin",methods=["GET","POST"])
def admin():
    if request.method=="POST":
        email=request.form["email"]
        password=request.form["password"]
        if email=="admin@safevoice.com" and password=="admin123":
            session["admin"]=True
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid Admin Credentials!","error")
    return render_template("admin.html")

@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin"))
    conn=sqlite3.connect("database.db")
    cursor=conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM reports")
    total_reports=cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users=cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM reports WHERE status='Pending'")
    pending=cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM reports WHERE status='Resolved'")
    resolved=cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM reports WHERE status='Reviewed'")
    reviewed=cursor.fetchone()[0]
    conn.close()
    return render_template("admin_dashboard.html",total_reports=total_reports,total_users=total_users,pending=pending,resolved=resolved,reviewed=reviewed)

@app.route("/admin_reports")
def admin_reports():
    if "admin" not in session:
        return redirect(url_for("admin"))
    search = request.args.get("search", "")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    if search:
        cursor.execute(
            """
            SELECT id, fullname, phone, location, incident_date,
                   description, ai_analysis, status, evidence
            FROM reports
            WHERE fullname LIKE ? OR location LIKE ?
            ORDER BY id DESC
            """,
            (f"%{search}%", f"%{search}%")
        )
    else:
        cursor.execute(
            """
            SELECT id, fullname, phone, location, incident_date,
                   description, ai_analysis, status, evidence
            FROM reports
            ORDER BY id DESC
            """
        )
    reports = cursor.fetchall()
    conn.close()
    return render_template("admin_reports.html", reports=reports, search=search)

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    if "admin" not in session:
        return redirect(url_for("admin"))
    return send_from_directory(app.config["UPLOAD_FOLDER"],filename)

@app.route("/update_status/<int:id>",methods=["GET","POST"])
def update_status(id):
    if "admin" not in session:
        return redirect(url_for("admin"))
    conn=sqlite3.connect("database.db")
    cursor=conn.cursor()
    if request.method=="POST":
        new_status=request.form["status"]
        cursor.execute("UPDATE reports SET status=? WHERE id=?",(new_status,id))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_reports"))
    cursor.execute("SELECT * FROM reports WHERE id=?",(id,))
    report=cursor.fetchone()
    conn.close()
    return render_template("update_status.html",report=report)

@app.route("/admin_logout")
def admin_logout():
    session.pop("admin",None)
    flash("Admin logged out successfully!","success")
    return redirect(url_for("admin"))

@app.route("/export_pdf")
def export_pdf():
    if "admin" not in session:
        return redirect(url_for("admin"))
    conn=sqlite3.connect("database.db")
    cursor=conn.cursor()
    cursor.execute("SELECT id,fullname,phone,location,incident_date,description,status FROM reports")
    reports=cursor.fetchall()
    conn.close()
    buffer=BytesIO()
    pdf=canvas.Canvas(buffer,pagesize=A4)
    width,height=A4
    pdf.setFont("Helvetica-Bold",18)
    pdf.drawString(50,height-50,"SafeVoice - Incident Reports")
    y=height-90
    pdf.setFont("Helvetica",10)
    for report in reports:
        text=f"ID: {report[0]} | Name: {report[1]} | Phone: {report[2]}"
        pdf.drawString(50,y,text)
        y-=18
        pdf.drawString(50,y,f"Location: {report[3]} | Date: {report[4]}")
        y-=18
        pdf.drawString(50,y,f"Status: {report[6]}")
        y-=18
        description=report[5]
        pdf.drawString(50,y,"Description:")
        y-=15
        words=description.split()
        line=""
        for word in words:
            if len(line+" "+word)>90:
                pdf.drawString(50,y,line)
                y-=15
                line=word
            else:
                line+=" "+word
        if line:
            pdf.drawString(50,y,line)
            y-=20
        pdf.line(50,y,width-50,y)
        y-=25
        if y<80:
            pdf.showPage()
            pdf.setFont("Helvetica",10)
            y=height-50
    pdf.save()
    buffer.seek(0)
    return send_file(buffer,as_attachment=True,download_name="SafeVoice_Reports.pdf",mimetype="application/pdf")

@app.route("/admin_users")
def admin_users():
    if "admin" not in session:
        return redirect(url_for("admin"))
    conn=sqlite3.connect("database.db")
    cursor=conn.cursor()
    cursor.execute("SELECT id, fullname, email, phone FROM users")
    users=cursor.fetchall()
    conn.close()
    return render_template("admin_users.html",users=users)

@app.route("/admin_analytics")
def admin_analytics():
    if "admin" not in session:
        return redirect(url_for("login"))
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM reports")
    total_reports = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM reports WHERE status='Pending'")
    pending = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM reports WHERE status='Reviewed'")
    reviewed = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM reports WHERE status='Resolved'")
    resolved = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM reports WHERE status='Rejected'")
    rejected = cursor.fetchone()[0]
    conn.close()
    return render_template(
        "admin_analytics.html",
        total_reports=total_reports,
        pending=pending,
        reviewed=reviewed,
        resolved=resolved,
        rejected=rejected
    )

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"),404
if __name__=="__main__":
    app.run(debug=True)