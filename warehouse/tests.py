from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from warehouse.models import Product, Wishlist, Category

class NotificationAndButtonTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass', email='test@gmail.com')
        self.user2 = User.objects.create_user(username='buyer', password='buyerpass', email='buyer@gmail.com')
        self.category = Category.objects.create(name='TestCat', slug='testcat')
        from warehouse.models import SellerProfile
        self.seller_profile = SellerProfile.objects.create(user=self.user, company_name='TestCo', description='desc', contact_number='123', address='addr')
        self.product = Product.objects.create(title='TestProduct', price=10, category=self.category, is_active=True, seller=self.seller_profile)

    def test_already_authenticated_message(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('sign_up'), follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('already signed in' in str(m) for m in messages))

    def test_profile_update_notification(self):
        self.client.login(username='testuser', password='testpass')
        url = reverse('setting')
        response = self.client.post(url, {'action': 'update_profile', 'username': 'testuser', 'email': 'test@gmail.com'}, follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('profile has been updated' in str(m) for m in messages))

    def test_switch_role_notification(self):
        self.client.login(username='testuser', password='testpass')
        url = reverse('switch_role')
        response = self.client.get(url, follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('now a seller' in str(m) or 'now a buyer' in str(m) for m in messages))

    def test_add_to_wishlist_notification(self):
        self.client.login(username='testuser', password='testpass')
        url = reverse('add_to_wishlist')
        response = self.client.post(url, {'product_id': self.product.id}, follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('added to your wishlist' in str(m) for m in messages))

    def test_remove_from_wishlist_notification(self):
        self.client.login(username='testuser', password='testpass')
        Wishlist.objects.create(user=self.user)
        url = reverse('remove_from_wishlist')
        response = self.client.post(url, {'product_id': self.product.id}, follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('removed from your wishlist' in str(m) or 'Wishlist not found' in str(m) for m in messages))

    def test_sign_up_gmail_only(self):
        response = self.client.post(reverse('sign_up'), {'username': 'newuser', 'email': 'notgmail@yahoo.com', 'password1': 'testpass123', 'password2': 'testpass123'}, follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Only @gmail.com' in str(m) for m in messages))

    def test_place_order_button_and_notification(self):
        # Setup: create a seller profile for the product
        from warehouse.models import SellerProfile
        seller_profile = SellerProfile.objects.create(user=self.user, company_name='TestCo', description='desc', contact_number='123', address='addr')
        self.product.seller = seller_profile
        self.product.save()
        self.client.login(username='testuser', password='testpass')
        # Add product to cart (simulate session)
        session = self.client.session
        session['cart'] = {str(self.product.id): {'quantity': 1, 'price': str(self.product.price)}}
        session.save()
        # Place order
        url = reverse('checkout')
        data = {
            'address': '123 Test St',
            'phone': '1234567890',
            f'select_{self.product.id}': True,
            f'quantity_{self.product.id}': 1
        }
        response = self.client.post(url, data, follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Order placed successfully' in str(m) for m in messages))
        # Check order exists
        from warehouse.models import Order
        self.assertTrue(Order.objects.filter(user=self.user, product=self.product).exists())

    def test_confirm_order_completion_notification(self):
        from warehouse.models import SellerProfile, Order
        seller_profile = SellerProfile.objects.create(user=self.user2, company_name='TestCo', description='desc', contact_number='123', address='addr')
        self.product.seller = seller_profile
        self.product.save()
        order = Order.objects.create(user=self.user, product=self.product, quantity=1, total_price=10, status='W')
        self.client.login(username='testuser', password='testpass')
        url = reverse('confirm_order_complete', args=[order.id])
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('success', response.json())
        self.assertTrue(response.json()['success'])
        # Check order status updated
        order.refresh_from_db()
        self.assertEqual(order.status, 'C')
