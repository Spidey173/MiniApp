from flask import Flask, render_template, request, jsonify, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "database.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Database Models


# Add new database models
class PasswordAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String(100), nullable=False)
    masked_password = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    strength = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    views = db.Column(db.Integer, default=0)
    last_accessed = db.Column(db.DateTime)


class Calculation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expression = db.Column(db.String(100), nullable=False)
    result = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(100), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def init_db():
    with app.app_context():
        db.create_all()

        # Seed projects if they don't exist
        projects = ['Calculator', 'Password Strength', 'Todo List', 'Notes', 'Stopwatch', 'Quotes']  # Updated here
        for name in projects:
            if not Project.query.filter_by(name=name).first():
                db.session.add(Project(name=name))
        db.session.commit()


# Update project views
def update_project_views(project_name):
    project = Project.query.filter_by(name=project_name).first()
    if project:
        project.views += 1
        project.last_accessed = datetime.utcnow()
        db.session.commit()


# Main Routes
@app.route('/')
def dashboard():
    projects = Project.query.all()
    total_views = sum(p.views for p in projects)
    calculations_count = Calculation.query.count()
    active_tasks = Todo.query.filter_by(completed=False).count()
    recent_calculations = Calculation.query.order_by(Calculation.created_at.desc()).limit(5).all()
    total_records = sum([
        Project.query.count(),
        Calculation.query.count(),
        Todo.query.count(),
        Note.query.count()
    ])

    return render_template('dashboard.html',
                           projects=projects,
                           total_views=total_views,
                           calculations_count=calculations_count,
                           active_tasks=active_tasks,
                           recent_calculations=recent_calculations,
                           total_records=total_records,
                           current_time=datetime.utcnow())


# Project Routes
@app.route('/calculator')
def calculator():
    update_project_views('Calculator')
    return render_template('projects/calculator.html')


@app.route('/password-strength')
def password_strength():
    update_project_views('Password Strength')
    return render_template('projects/password_strength.html')


@app.route('/api/log_password', methods=['POST'])
def log_password():
    data = request.json
    password = data['password']

    # Create masked version (first 2 chars, last 2 chars, middle masked)
    if len(password) > 4:
        masked = password[:2] + '*' * (len(password) - 4) + password[-2:]
    else:
        masked = '*' * len(password)

    new_analysis = PasswordAnalysis(
        password=password,
        masked_password=masked,
        score=data['score'],
        strength=data['strength']
    )

    db.session.add(new_analysis)
    db.session.commit()

    return jsonify({'status': 'success'}), 201


@app.route('/api/password_history')
def password_history():
    history = PasswordAnalysis.query.order_by(PasswordAnalysis.timestamp.desc()).limit(10).all()

    return jsonify([{
        'id': item.id,
        'masked_password': item.masked_password,
        'score': item.score,
        'strength': item.strength,
        'timestamp': item.timestamp.isoformat()
    } for item in history])


@app.route('/todo')
def todo():
    update_project_views('Todo List')
    return render_template('projects/todo.html')


@app.route('/notes')
def notes():
    update_project_views('Notes')
    return render_template('projects/notes.html')


@app.route('/stopwatch')
def stopwatch():
    update_project_views('Stopwatch')
    return render_template('projects/stopwatch.html')


@app.route('/quotes')
def quotes():
    update_project_views('Quotes')
    return render_template('projects/quotes.html')


# API Endpoints
@app.route('/api/log_calculation', methods=['POST'])
def log_calculation():
    data = request.json
    new_calc = Calculation(
        expression=data['expression'],
        result=data['result']
    )
    db.session.add(new_calc)
    db.session.commit()
    return jsonify({'status': 'success'}), 201


@app.route('/api/todos', methods=['GET', 'POST'])
def todos_api():
    if request.method == 'GET':
        todos = Todo.query.order_by(Todo.created_at.desc()).all()
        return jsonify([{
            'id': t.id,
            'task': t.task,
            'completed': t.completed,
            'created_at': t.created_at.isoformat()
        } for t in todos])

    elif request.method == 'POST':
        data = request.json
        new_todo = Todo(task=data['task'])
        db.session.add(new_todo)
        db.session.commit()
        return jsonify({
            'id': new_todo.id,
            'task': new_todo.task,
            'completed': new_todo.completed
        }), 201


@app.route('/api/todos/<int:todo_id>', methods=['PUT', 'DELETE'])
def todo_api(todo_id):
    todo = Todo.query.get_or_404(todo_id)

    if request.method == 'PUT':
        data = request.json
        todo.task = data.get('task', todo.task)
        todo.completed = data.get('completed', todo.completed)
        db.session.commit()
        return jsonify({'status': 'success'})

    elif request.method == 'DELETE':
        db.session.delete(todo)
        db.session.commit()
        return jsonify({'status': 'deleted'})


@app.route('/api/notes', methods=['GET', 'POST'])
def notes_api():
    if request.method == 'GET':
        notes = Note.query.order_by(Note.created_at.desc()).all()
        return jsonify([{
            'id': n.id,
            'content': n.content,
            'created_at': n.created_at.isoformat()
        } for n in notes])

    elif request.method == 'POST':
        data = request.json
        new_note = Note(content=data['content'])
        db.session.add(new_note)
        db.session.commit()
        return jsonify({
            'id': new_note.id,
            'content': new_note.content
        }), 201


@app.route('/api/notes/<int:note_id>', methods=['PUT', 'DELETE'])
def note_api(note_id):
    note = Note.query.get_or_404(note_id)

    if request.method == 'PUT':
        data = request.json
        note.content = data.get('content', note.content)
        db.session.commit()
        return jsonify({'status': 'success'})

    elif request.method == 'DELETE':
        db.session.delete(note)
        db.session.commit()
        return jsonify({'status': 'deleted'})


# Run the Application
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5003)