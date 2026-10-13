from ecommerce_server import app, db, User

# Direct script run karne ka logic
with app.app_context():
    number = "7218781434"
    user = User.query.filter_by(mobile=number).first()
    
    if user:
        user.is_admin = True
        db.session.commit()
        print(f"🎉 Success! {number} ab ADMIN ban gaya hai.")
    else:
        print(f"❌ Error: {number} naam ka koi user database me nahi mila. Pehle App me signup/login karein.")
