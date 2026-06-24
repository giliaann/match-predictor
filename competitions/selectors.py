def get_competition_details_data(competition, user, request_stage=None, request_group=None):
    
    all_stages = list(competition.matches.values_list('stage', flat=True).distinct().order_by('stage'))
    current_stage = request_stage or (all_stages[0] if all_stages else None)

    all_groups = []
    current_group = None
    if current_stage:
        groups = competition.matches.filter(stage=current_stage).values_list('group', flat=True).distinct().order_by('group')
        all_groups = [g for g in groups if g]
        current_group = request_group or (all_groups[0] if all_groups else None)

    match_filter = {'competition': competition, 'stage': current_stage}
    if current_group:
        match_filter['group'] = current_group
    matches = competition.matches.filter(**match_filter).select_related('home_team', 'away_team').order_by('kickoff_time')

    is_registered = False
    if user.is_authenticated:
        registration = competition.registrations.filter(user=user).first()
        if registration:
            is_registered = True
            user_predictions = {pred.match_id: pred for pred in registration.predictions.all()}
            for match in matches:
                match.user_prediction = user_predictions.get(match.id)

    return {
        'all_stages': all_stages,
        'current_stage': current_stage,
        'all_groups': all_groups,
        'current_group': current_group,
        'matches': matches,
        'is_registered': is_registered,
    }