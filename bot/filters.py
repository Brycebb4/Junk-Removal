class LeadFilter:
    def __init__(self, keywords, priority_scores):
        self.keywords = keywords  # List of keywords for filtering
        self.priority_scores = priority_scores  # Dictionary with lead identifiers as keys and priority scores as values

    def filter_leads(self, leads):
        filtered_leads = []
        for lead in leads:
            score = self.get_priority_score(lead['id'])
            if self.matches_keywords(lead['description']):
                filtered_leads.append((lead, score))
        return filtered_leads

    def get_priority_score(self, lead_id):
        return self.priority_scores.get(lead_id, 0)  # Default to 0 if not found

    def matches_keywords(self, description):
        return any(keyword in description for keyword in self.keywords  # Check if any keyword is present in the description
        )