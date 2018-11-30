from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
from app.models import User


class LoginForm(FlaskForm):
    username = StringField("utilizador", validators=[DataRequired()])
    password = PasswordField("password", validators=[DataRequired()])
    remember_me = BooleanField("Lembra-te de mim")
    submit = SubmitField("entrar")


class RegistrationForm(FlaskForm):
    username = StringField("utilizador", validators=[DataRequired()])
    email = StringField("email", validators=[DataRequired(), Email()])
    password = PasswordField("password", validators=[DataRequired()])
    password2 = PasswordField(
        "password (sim, outra vez)",
        validators=[DataRequired(), EqualTo("password")],
    )
    submit = SubmitField("registar")

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError("Esse username tem dono já.")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError("Esse email outra vez?.")


class ResetPasswordRequestForm(FlaskForm):
    email = StringField("email", validators=[DataRequired(), Email()])
    submit = SubmitField("repor password")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("password", validators=[DataRequired()])
    password2 = PasswordField(
        "repete a password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Repor")
