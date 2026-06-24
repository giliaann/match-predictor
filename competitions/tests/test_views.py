from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.messages import get_messages
from unittest.mock import patch
from datetime import date

from competitions.models import Competition

User = get_user_model()

class CompetitionViewsTests(TestCase):
    def setUp(self):
        
        self.user = User.objects.create_user(username='testplayer', password='password123')
        
        
        self.comp1 = Competition.objects.create(
            api_id=101, season_api_id=2024, name="World Cup", code="WC",
            date_start=date(2026, 6, 11), date_finish=date(2026, 7, 19), emblem="url1"
        )
        self.comp2 = Competition.objects.create(
            api_id=102, season_api_id=2023, name="Euro", code="EUR",
            date_start=date(2024, 6, 14), date_finish=date(2024, 7, 14), emblem="url2"
        )
        
        self.list_url = reverse('competition_list')
        self.detail_url = reverse('competition_detail', kwargs={'code': self.comp1.code})
        self.leave_url = reverse('competition_leave', kwargs={'code': self.comp1.code})


    def test_competition_list_view_status_and_template(self):
        """Checks if the list view returns 200 OK and uses the correct template."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'competitions/competition_list.html')

    def test_competition_list_view_queryset_ordering(self):
        """Checks if competitions are passed to the context and ordered by -date_start."""
        response = self.client.get(self.list_url)
        competitions = response.context['competitions']
        
        self.assertEqual(len(competitions), 2)
        # comp1 starts in 2026, comp2 starts in 2024. Descending order means comp1 should be first.
        self.assertEqual(competitions[0], self.comp1)
        self.assertEqual(competitions[1], self.comp2)



    @patch('competitions.views.selectors.get_competition_details_data')
    def test_competition_detail_view_success(self, mock_get_details):
        """Checks if the detail view correctly fetches the competition and calls the selector."""
    
        fake_details = {
            'all_stages': ['GROUP_STAGE'],
            'current_stage': 'GROUP_STAGE',
            'all_groups': ['GROUP_A'],
            'current_group': 'GROUP_A',
            'matches': [],
            'is_registered': True
        }
        mock_get_details.return_value = fake_details

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'competitions/competition_detail.html')
        self.assertEqual(response.context['competition'], self.comp1)
        
      
        self.assertTrue(response.context['is_registered'])
        self.assertEqual(response.context['current_stage'], 'GROUP_STAGE')

        
        mock_get_details.assert_called_once_with(
            competition=self.comp1,
            user=response.wsgi_request.user,
            request_stage=None,
            request_group=None
        )

    @patch('competitions.views.selectors.get_competition_details_data')
    def test_competition_detail_view_with_query_params(self, mock_get_details):
        """Checks if the view passes GET parameters (stage and group) to the selector."""
        mock_get_details.return_value = {}
        
        self.client.force_login(self.user)

        # Access URL with query parameters: ?stage=FINAL&group=NONE
        self.client.get(f"{self.detail_url}?stage=FINAL&group=NONE")
        
        mock_get_details.assert_called_once_with(
            competition=self.comp1,
            user=self.user,
            request_stage='FINAL',
            request_group='NONE'
        )

    def test_competition_detail_view_404(self):
        """Accessing a non-existent competition code should return a 404 Not Found."""
        bad_url = reverse('competition_detail', kwargs={'code': 'INVALID'})
        response = self.client.get(bad_url)
        self.assertEqual(response.status_code, 404)



    def test_competition_leave_view_requires_login(self):
        """Unauthenticated users should be redirected to the login page."""
        response = self.client.post(self.leave_url)
        # 302 Redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/users/login/')) 

    @patch('competitions.views.services.leave_competition')
    def test_competition_leave_view_success(self, mock_leave_competition):
        """A successful POST request should call the service, set a success message, and redirect to list."""
        self.client.force_login(self.user)
        
        mock_leave_competition.return_value = None 

        response = self.client.post(self.leave_url)

        self.assertRedirects(response, self.list_url)
        
       
        mock_leave_competition.assert_called_once_with(user=self.user, competition=self.comp1)

    
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), f"You have successfully left the competition: {self.comp1.name}.")

    @patch('competitions.views.services.leave_competition')
    def test_competition_leave_view_validation_error(self, mock_leave_competition):
        """If the service raises a ValidationError, it should redirect to the detail page and show an error."""
        self.client.force_login(self.user)
        
        # Simulate the service blocking the user from leaving
        error_message = "You cannot leave this competition because you are an administrator."
        mock_leave_competition.side_effect = ValidationError(error_message)

        response = self.client.post(self.leave_url)

        # Should redirect back to the competition detail page
        self.assertRedirects(response, self.detail_url)

        # Check messages
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), error_message)