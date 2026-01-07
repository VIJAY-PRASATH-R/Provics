# Tests module imports
import unittest
from app import app, db, User


class IVPlannerTestCase(unittest.TestCase):
  def setUp(self):
        """Set up test database and client"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        """Clean up after test"""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_index_loads(self):
        """Test if homepage loads correctly"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'IV Connector', response.data)

    def test_register_user(self):
        """Test user registration"""
        response = self.client.post('/register', data=dict(
            name='Test User',
            email='new@test.com',
            password='password123',
            role='student'
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Registration successful', response.data)
        
        with app.app_context():
            user = User.query.filter_by(email='new@test.com').first()
            self.assertIsNotNone(user)
            self.assertEqual(user.role, 'student')

if __name__ == '__main__':
    unittest.main()
