from ecommerce_server import app, db, Category
with app.app_context():
    cat0=Category(name='Electronics')
    # 1. 3 नई कैटेगरीज़ बनाईं
    cat1 = Category(name="Grocery")
    cat2 = Category(name="Fashion")
    cat3 = Category(name="Home Appliances")

    # 2. डेटाबेस में सेव किया
    db.session.add_all([cat1, cat2, cat3])
    db.session.commit()

    print("✅ Categories successfully created in DB!")
