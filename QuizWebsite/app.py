from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

# -----------------------
# Configuration
# -----------------------
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "YourSecretKey"

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# Helper function for safe commit
def commit_changes():
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("Database commit error:", e)
        flash("A database error occurred: " + str(e), "danger")
        return False
    return True

# -----------------------
# Models
# -----------------------

class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="user")
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class QuizResult(db.Model):
    __tablename__ = "quiz_result"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    genre = db.Column(db.String(50))
    score = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Existing single-question custom quiz models (if any) remain unchanged…
# Now, add new models for multi-question custom quizzes:

class CustomQuizMaster(db.Model):
    __tablename__ = 'custom_quiz_master'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    created_by = db.Column(db.String(100), nullable=False)  # storing creator's name
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='pending')  # e.g. pending, active
    questions = db.relationship('CustomQuizQuestion', backref='quiz', lazy=True)

class CustomQuizQuestion(db.Model):
    __tablename__ = 'custom_quiz_question'
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('custom_quiz_master.id'), nullable=False)
    question_text = db.Column(db.String(255), nullable=False)
    option1 = db.Column(db.String(255), nullable=False)
    option2 = db.Column(db.String(255), nullable=False)
    option3 = db.Column(db.String(255), nullable=False)
    option4 = db.Column(db.String(255), nullable=False)
    correct_option = db.Column(db.Integer, nullable=False)  # 0, 1, 2, or 3

class CustomQuizAttempt(db.Model):
    __tablename__ = 'custom_quiz_attempt'
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('custom_quiz_master.id'), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# -----------------------
# Trivia Quiz Dummy Data & Routes
# -----------------------

genre_questions = {
    'music': [
        {"question": "Who is the King of Pop?", "options": ["Michael Jackson", "Elvis Presley", "Justin Bieber"], "answer": "Michael Jackson"},
        {"question": "Which band recorded 'Hey Jude'?", "options": ["The Beatles", "The Rolling Stones", "Queen"], "answer": "The Beatles"},
    ],
    'language': [
        {"question": "What is the official language of Brazil?", "options": ["Spanish", "Portuguese", "English"], "answer": "Portuguese"},
        {"question": "Which language is primarily spoken in Canada?", "options": ["French", "Spanish", "English"], "answer": "English"},
    ],
    'puzzle': [
        {"question": "Which number completes the sequence: 1, 4, 9, 16, ?", "options": ["25", "36", "49"], "answer": "25"},
        {"question": "What is the square root of 64?", "options": ["6", "7", "8"], "answer": "8"},
    ],
    'math': [
        {"question": "What is 12 + 7?", "options": ["18", "19", "20"], "answer": "19"},
        {"question": "What is 9 * 9?", "options": ["72", "81", "90"], "answer": "81"},
    ]
}

@app.route('/')
def start_page():
    return render_template('start.html')

@app.route('/home')
@login_required
def home():
    return render_template('home.html')

@app.route('/quiz/music')
def music_quiz():
    return render_template('music_quiz.html')

@app.route('/quiz/puzzle')
def puzzle_quiz():
    return render_template('puzzle_quiz.html')

@app.route('/quiz/math')
def math_quiz():
    return render_template('math_quiz.html')

@app.route('/quiz/language')
def language_quiz():
    return render_template('language_quiz.html')

@app.route('/start_quiz/<genre>')
def start_quiz(genre):
    session.clear()
    session['genre'] = genre
    session['question_index'] = 0
    session['score'] = 0
    session['answers'] = []
    return redirect(url_for('question'))

@app.route('/question', methods=['GET', 'POST'])
def question():
    genre = session.get('genre', 'music')
    questions = genre_questions.get(genre, [])
    index = session.get('question_index', 0)
    if index >= len(questions):
        return redirect(url_for('result'))
    q = questions[index]
    return render_template('question.html', question=q["question"], options=q["options"], index=index + 1, total=len(questions), genre=genre)

@app.route('/next', methods=['POST'])
def next_question():
    genre = session.get('genre', 'music')
    questions = genre_questions.get(genre, [])
    index = session.get('question_index', 0)
    selected_option = request.form.get("answer")
    if 'answers' not in session:
        session['answers'] = []
    if selected_option:
        session['answers'].append(selected_option)
        session.modified = True
        if selected_option == questions[index]["answer"]:
            session['score'] += 1
    session['question_index'] += 1
    return redirect(url_for('question'))

@app.route('/result')
def result():
    genre = session.get('genre', 'music')
    questions = genre_questions.get(genre, [])
    score = session.get('score', 0)
    total = len(questions)
    passed = (score / total) * 100 >= 70
    answers = session.get('answers', [])
    questions_with_answers = list(zip(questions, answers))
    return render_template('result.html', score=score, total=total, passed=passed, questions_with_answers=questions_with_answers, genre=genre)

# -----------------------
# Trivia Quiz External API Routes (unchanged)
# -----------------------

OPEN_TRIVIA_URL = "https://opentdb.com/api.php"

@app.route('/create_quiz')
def create_quiz():
    return render_template('create_quiz.html')

@app.route('/get_questions', methods=['POST'])
def get_questions_api():
    data = request.json
    amount = data.get('amount', 10)
    category = data.get('category', 'General Knowledge')
    difficulty = data.get('difficulty', '')
    category_ids = {
        "General Knowledge": 9,
        "Science & Nature": 17,
        "Computers": 18,
        "Mathematics": 19,
        "History": 23,
        "Sports": 21
    }
    params = {
        'amount': amount,
        'category': category_ids.get(category, ''),
        'difficulty': difficulty.lower() if difficulty else '',
        'type': 'multiple'
    }
    response = requests.get(OPEN_TRIVIA_URL, params=params)
    if response.status_code == 200:
        return jsonify(response.json()['results'])
    else:
        return jsonify({'error': 'Failed to fetch questions'}), 500

@app.route('/save_quiz', methods=['POST'])
def save_quiz():
    data = request.get_json()
    username = data.get('username', 'Guest')
    genre = data.get('genre', 'General')
    score = data.get('score')
    total = data.get('total')
    if score is None or total is None:
        return jsonify({'error': 'Missing score or total'}), 400
    try:
        score = int(score)
        total = int(total)
    except ValueError:
        return jsonify({'error': 'Invalid score or total'}), 400
    new_result = QuizResult(username=username, genre=genre, score=score, total=total)
    db.session.add(new_result)
    if not commit_changes():
        return jsonify({'error': 'Failed to save quiz result'}), 500
    return jsonify({'message': 'Quiz result saved successfully!'})

# -----------------------
# Leaderboard Route (Integrated)
# -----------------------
@app.route('/leaderboard')
def leaderboard():
    # Trivia Leaderboard Aggregation (Sorted Descending)
    trivia = db.session.query(
        QuizResult.username,
        db.func.count(QuizResult.id).label("quiz_count"),
        db.func.sum(QuizResult.score).label("total_score")
    ).group_by(QuizResult.username).all()
    main_leaderboard = [{
        "username": row.username,
        "quiz_count": row.quiz_count,
        "total_score": row.total_score
    } for row in trivia]

    # Build quiz_details dictionary: map each username to a list of quiz attempts
    quiz_details = {}
    all_results = QuizResult.query.order_by(QuizResult.timestamp.desc()).all()
    for result in all_results:
        detail = {
            "genre": result.genre,
            "score": result.score,
            "total": result.total,
            "timestamp": result.timestamp.strftime("%Y-%m-%d %H:%M")
        }
        if result.username in quiz_details:
            quiz_details[result.username].append(detail)
        else:
            quiz_details[result.username] = [detail]

    # Custom Quiz Aggregation
    custom = db.session.query(
        User.name.label("username"),
        db.func.count(CustomQuizAttempt.id).label("quiz_count"),
        db.func.sum(CustomQuizAttempt.score).label("total_score")
    ).join(User, User.id == CustomQuizAttempt.user_id).group_by(User.name).all()
    custom_aggregated = [{
        "username": row.username,
        "quiz_count": row.quiz_count,
        "total_score": row.total_score
    } for row in custom]

    # Pending Custom Quizzes
    pending_quizzes = CustomQuizMaster.query.filter_by(status='pending').all()

    # For the trivia bar graph, we use main_leaderboard data (assuming it's already sorted)
    aggregated_json = sorted(main_leaderboard, key=lambda x: x['total_score'], reverse=True)

    return render_template('leaderboard.html',
                           main_leaderboard=main_leaderboard,
                           custom_aggregated=custom_aggregated,
                           pending_quizzes=pending_quizzes,
                           aggregated_json=aggregated_json,
                           quiz_details=quiz_details)

# -----------------------
# Custom Quiz (Multi-Question) Functionality
# -----------------------

# Route to create a custom quiz using your provided create_custom_quiz template
@app.route('/create_custom_quiz', methods=['GET', 'POST'])
@login_required
def create_custom_quiz():
    if request.method == 'POST':
        title = request.form.get('title')
        subject = request.form.get('subject')
        try:
            num_questions = int(request.form.get('num_questions'))
        except:
            flash("Invalid number of questions.", "danger")
            return redirect(url_for('create_custom_quiz'))
        
        # Create quiz master record
        quiz = CustomQuizMaster(
            title=title,
            subject=subject,
            created_by=current_user.name,
            status='pending'
        )
        db.session.add(quiz)
        db.session.flush()  # Get quiz.id before commit
        
        # Loop over each question and create question records
        for i in range(1, num_questions+1):
            q_text = request.form.get(f'question_{i}')
            op1 = request.form.get(f'q{i}_option1')
            op2 = request.form.get(f'q{i}_option2')
            op3 = request.form.get(f'q{i}_option3')
            op4 = request.form.get(f'q{i}_option4')
            correct = request.form.get(f'q{i}_correct')
            if None in [q_text, op1, op2, op3, op4, correct]:
                flash("Please fill all fields for each question.", "danger")
                return redirect(url_for('create_custom_quiz'))
            try:
                correct = int(correct)
            except:
                flash("Invalid correct answer for question " + str(i), "danger")
                return redirect(url_for('create_custom_quiz'))
            question_obj = CustomQuizQuestion(
                quiz_id=quiz.id,
                question_text=q_text,
                option1=op1,
                option2=op2,
                option3=op3,
                option4=op4,
                correct_option=correct
            )
            db.session.add(question_obj)
        if not commit_changes():
            return redirect(url_for('create_custom_quiz'))
        flash("Custom quiz created successfully!", "success")
        return redirect(url_for('custom_quizzes'))
    return render_template('create_custom_quiz.html')


@app.route('/pending_custom_quizzes')
@login_required
def pending_custom_quizzes():
    pending_quizzes = CustomQuizMaster.query.filter_by(status='pending').all()
    return render_template('pending_custom_quizzes.html', pending_quizzes=pending_quizzes)


# Route to list all custom quizzes (for example, in a grid) – using your provided custom_quizzes.html
@app.route('/custom_quizzes')
@login_required
def custom_quizzes():
    quizzes = CustomQuizMaster.query.all()
    return render_template('custom_quizzes.html', quizzes=quizzes)

# Route to take a custom quiz – displays one question at a time using your custom_quiz_question.html template
@app.route('/take_custom/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def take_custom(quiz_id):
    quiz = CustomQuizMaster.query.get_or_404(quiz_id)
    questions = quiz.questions
    total = len(questions)

    if 'custom_index' not in session or session.get('current_quiz_id') != quiz_id:
        session['custom_index'] = 0
        session['custom_score'] = 0
        session['current_quiz_id'] = quiz_id

    index = session['custom_index']

    if request.method == 'POST':
        selected = request.form.get('answer')
        if selected is None:
            flash("Please select an option.", "warning")
            return redirect(url_for('take_custom', quiz_id=quiz_id))

        try:
            selected = int(selected)
        except ValueError:
            flash("Invalid answer.", "warning")
            return redirect(url_for('take_custom', quiz_id=quiz_id))

        current_question = questions[index]
        if selected == current_question.correct_option:
            session['custom_score'] += 1

        session['custom_index'] += 1
        index = session['custom_index']

        if index >= total:
            score = session['custom_score']
            attempt = CustomQuizAttempt(
                quiz_id=quiz.id,
                user_id=current_user.id,
                score=score,
                total=total
            )
            db.session.add(attempt)

            # Update the quiz status to 'completed'
            quiz.status = 'completed'
            db.session.commit()

            session.pop('custom_index', None)
            session.pop('custom_score', None)
            session.pop('current_quiz_id', None)

            return redirect(url_for('custom_result', quiz_id=quiz.id, score=score, total=total))

    if index < total:
        current_question = questions[index]
        options = [current_question.option1, current_question.option2, current_question.option3, current_question.option4]
        return render_template('custom_quiz_question.html', question=current_question.question_text, options=options, index=index+1, total=total)

    return redirect(url_for('home'))

# Route to display custom quiz result using your provided custom_result.html
@app.route('/custom_result')
@login_required
def custom_result():
    # Retrieve query parameters as integers
    quiz_id = request.args.get('quiz_id', type=int)
    score = request.args.get('score', type=int)
    total = request.args.get('total', type=int)
    
    if quiz_id is None or score is None or total is None:
        flash("Missing quiz result parameters.", "danger")
        return redirect(url_for('home'))
    
    # For a single-question custom quiz, use the CustomQuiz model.
    quiz = CustomQuizMaster.query.get(quiz_id)
    if not quiz:
        flash("Quiz not found.", "danger")
        return redirect(url_for('leaderboard'))
    
    # Use quiz.question as the title (since your model stores the quiz text in 'question')
    percentage = round((score/total)*100, 2) if total > 0 else 0
    return render_template('custom_results.html',
                           quiz_title=quiz.title,
                           score=score,
                           total=total,
                           percentage=percentage)

# -----------------------
# User Registration & Login Routes (unchanged)
# -----------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        mobile = request.form.get("mobile")
        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("register"))
        if User.query.filter_by(email=email).first():
            flash("Email already exists! Please log in.", "danger")
            return redirect(url_for("login"))
        new_user = User(name=name, email=email, mobile=mobile, role="user")
        new_user.set_password(password)
        db.session.add(new_user)
        if not commit_changes():
            return redirect(url_for("register"))
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("No account found! Please register first.", "warning")
            return redirect(url_for("register"))
        if not user.check_password(password):
            flash("Invalid email or password!", "danger")
            return redirect(url_for("login"))
        login_user(user)
        flash("Login successful!", "success")
        return redirect(url_for("home"))
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route('/contactus')
def contactus():
    return render_template('contactus.html')

@app.route('/blog')
def blog():
    return render_template('contactus.html')



@app.route('/profile')
@login_required  # Ensure that only logged-in users can access the profile page
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        # Update user information
        current_user.name = request.form.get('name')
        current_user.email = request.form.get('email')
        current_user.mobile = request.form.get('mobile')
        if 'profile_pic' in request.files:
            profile_pic = request.files['profile_pic']
            if profile_pic.filename:
                profile_pic.save(f"static/uploads/{profile_pic.filename}")  # Save image
     
        db.session.commit()
        session['profile_updated'] = True
        return redirect(url_for('home'))

       

    return render_template('edit_profile.html', user=current_user)

# -----------------------
# Main Entry Point
# -----------------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
