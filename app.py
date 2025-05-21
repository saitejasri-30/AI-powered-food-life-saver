from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, date
from apscheduler.schedulers.background import BackgroundScheduler
import pytesseract
from PIL import Image
import requests
import os

# Set Tesseract path for Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

# Database model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    type = db.Column(db.String(50))  # food, grocery, daily, non-grocery
    purchase_date = db.Column(db.String(10))
    expiry_date = db.Column(db.String(10))
    alert_sent = db.Column(db.Boolean, default=False)

# OCR processing
def extract_text(image_path):
    img = Image.open(image_path)
    return pytesseract.image_to_string(img)

# Temperature-based expiry adjustment
def adjust_expiry_by_temperature(item_name, base_days):
    API_KEY = "your_openweather_api_key"
    CITY = "Hyderabad"
    url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric"
    try:
        temp = requests.get(url).json()['main']['temp']
        if item_name.lower() in ['banana','berries','tomatoes'] and temp > 30:
            return base_days - 2
    except:
        pass
    return base_days

# Recipe suggestions
recipes = {
    ('milk','bread'): 'French Toast',
    ('eggs','cheese'): 'Cheese Omelette',
    ('tomatoes','onions'): 'Tomato Soup',
    ('chicken','rice'): 'Chicken Fried Rice',
    ('potatoes','cheese'): 'Cheesy Mashed Potatoes'
}
def suggest_recipe(selected):
    return [r for ing, r in recipes.items() if any(item in selected for item in ing)]

# Scheduler to check expiry
def check_expiry():
    today = date.today()
    for item in Product.query.all():
        if datetime.strptime(item.expiry_date,'%Y-%m-%d').date() <= today and not item.alert_sent:
            print(f"ALERT: {item.name} expired on {item.expiry_date}")
            item.alert_sent = True
            db.session.commit()

scheduler = BackgroundScheduler()
scheduler.add_job(check_expiry,'interval',hours=24)
scheduler.start()

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/add',methods=['POST'])
def add_product():
    data = request.json
    days = data.get('shelf_life', 7)
    adjusted = adjust_expiry_by_temperature(data['name'], days)
    exp = (datetime.strptime(data['purchase_date'],'%Y-%m-%d') + timedelta(days=adjusted)).strftime('%Y-%m-%d')
    p = Product(name=data['name'], type=data['type'], purchase_date=data['purchase_date'], expiry_date=exp)
    db.session.add(p)
    db.session.commit()
    return jsonify(message="Item added", expiry_date=exp)

@app.route('/receipt',methods=['POST'])
def upload_receipt():
    f = request.files['receipt']
    path = os.path.join('uploads', f.filename)
    f.save(path)
    text = extract_text(path)
    os.remove(path)
    return jsonify(extracted_text=text)

@app.route('/recipes',methods=['POST'])
def get_recipes():
    return jsonify(suggestions=suggest_recipe(request.json.get('ingredients', [])))

@app.route('/items')
def get_items():
    return jsonify([{
        'id': i.id,
        'name': i.name,
        'type': i.type,
        'purchase_date': i.purchase_date,
        'expiry_date': i.expiry_date
    } for i in Product.query.all()])

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    with app.app_context():
        db.create_all()
    app.run(debug=True)
