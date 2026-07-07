# app.py
from flask import Flask, render_template, session, redirect, url_for


@app.route("/")
def intro():
    if session.get("intro_visto"):
        return redirect(url_for("home"))
    return render_template("intro.html")
