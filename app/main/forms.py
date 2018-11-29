from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import (
    ValidationError,
    DataRequired,
    Email,
    Length,
    URL,
    Optional,
)
from app.models import User


class EditProfileForm(FlaskForm):
    username = StringField("nome de utilizador", validators=[DataRequired()])
    about_me = TextAreaField("sobre mim", validators=[Length(min=0, max=140)])
    email = StringField("email", validators=[DataRequired(), Email()])
    submit = SubmitField("submeter")

    def __init__(self, original_username, original_email, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError("Please use a different username.")

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=self.email.data).first()
            if user is not None:
                raise ValidationError("Please use a different email.")


class PostForm(FlaskForm):
    title = StringField(
        "titulo", validators=[DataRequired(), Length(min=1, max=80)]
    )
    text = TextAreaField(
        "texto", validators=[Optional(), Length(min=1, max=280)]
    )
    url = StringField("link", validators=[Optional(), URL()])
    submit = SubmitField("submeter")

    def validate_text(self, text):
        if len(self.url.data) > 0:
            raise ValidationError("Please choose text or link post.")

    def validate_url(self, url):
        if len(self.text.data) > 0:
            raise ValidationError("Please choose text or link post.")


class CommentForm(FlaskForm):
    text = TextAreaField(
        "Comment Text", validators=[DataRequired(), Length(min=1, max=280)]
    )
    submit = SubmitField("Comentar")
