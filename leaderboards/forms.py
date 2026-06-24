from django import forms

class JoinLeaderboardForm(forms.Form):
    join_code = forms.CharField(
        max_length=16, 
        label="Invite Code",
        widget=forms.TextInput(attrs={'placeholder': 'e.g. 1A2B3C4D'})
    )