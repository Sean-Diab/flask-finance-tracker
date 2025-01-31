import unittest
from app import app, db, User

class TestFinanceApp(unittest.TestCase):
    
    def setUp(self):
        # Configure the app for testing
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_finance.db'
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        with app.app_context():
            db.drop_all()

    def test_register_and_login(self):
        # Register user
        response = self.client.post('/register', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        self.assertIn(b'Registration successful', response.data)
        
        # Login user
        response = self.client.post('/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        self.assertIn(b'Logged in successfully!', response.data)

    def test_dashboard_requires_login(self):
        response = self.client.get('/dashboard', follow_redirects=True)
        self.assertIn(b'Please log in to access this page.', response.data)

if __name__ == '__main__':
    unittest.main()