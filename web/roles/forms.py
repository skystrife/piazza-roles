from flask_wtf import FlaskForm
from wtforms import DecimalField, IntegerField
from wtforms.validators import DataRequired, NumberRange


class AnalysisForm(FlaskForm):
    session_gap = DecimalField(
        'Session gap length (hours)',
        places=1,
        validators=[DataRequired(), NumberRange(min=0.5)],
        render_kw={
            'step': '0.5',
            'min': '0.5'
        })

    role_count = IntegerField(
        'Number of roles',
        validators=[DataRequired(), NumberRange(min=2)],
        render_kw={'min': '2'})

    max_iterations = IntegerField(
        'Number of iterations',
        validators=[DataRequired(),
                    NumberRange(min=100, max=5000)],
        render_kw={
            'min': '100',
            'max': '5000'
        })

    proportion_smoothing = DecimalField(
        'Proportion smoothing',
        places=2,
        validators=[DataRequired(), NumberRange(min=0.01)],
        render_kw={
            'step': '0.01',
            'min': '0.01'
        })

    role_smoothing = DecimalField(
        'Role smoothing',
        places=2,
        validators=[DataRequired(), NumberRange(min=0.01)],
        render_kw={
            'step': '0.01',
            'min': '0.01'
        })
