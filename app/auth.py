from . import login_manager
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from .models import db, User


auth = Blueprint("auth", __name__)

# flask-login loader


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# register
@auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        if User.query.filter_by(email=email).first():
            flash("Email already registered!", "danger")
            return redirect(url_for("auth.register"))

        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()
        flash("Account created successfully! Please Log in.", "success")
        return redirect(url_for('auth.login'))

    return render_template("register.html")


# Login
@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash("Login successful", "success")

            # ✅ Check if user tried to access a protected page first
            next_page = request.args.get("next")

            return redirect(next_page) if next_page else redirect(url_for('main.home'))

        else:
            flash("Invalid creadentials!", "danger")
            return redirect(url_for('auth.login'))

    return render_template("login.html")

# logout


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.home"))
