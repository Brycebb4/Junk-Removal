class LeadFilter:
    def __init__(self):
        self.high_value_keywords = ['garage cleanout', 'estate cleanout', 'moving debris', 'construction waste', 'hoarder']
        self.medium_value_keywords = ['junk removal', 'furniture removal', 'appliance removal']
        self.negative_keywords = ['curbside', 'free dirt', 'scrap metal only', 'donation pickup']

    def process(self, lead):
        """
        Process a lead and determine if it passes filters
        Returns filtered lead with priority score or None if filtered out
        """
        text = (lead.get('title', '') + ' ' + lead.get('description', '')).lower()
        
        # Check negative keywords first
        for keyword in self.negative_keywords:
            if keyword in text:
                return None
        
        # Calculate priority score
        score = self._calculate_score(text, lead)
        
        if score < 30:
            return None
        
        # Add score to lead
        lead['priority_score'] = score
        lead['status'] = 'new'
        return lead

    def _calculate_score(self, text, lead):
        """Calculate priority score 0-100"""
        score = 0
        
        # High-value keywords: 30 points each
        for keyword in self.high_value_keywords:
            if keyword in text:
                score += 30
                break
        
        # Medium-value keywords: 15 points each
        for keyword in self.medium_value_keywords:
            if keyword in text:
                score += 15
                break
        
        # Location bonus for high-value zip codes
        location = lead.get('location', '').upper()
        tier_1_zips = ['45040', '45069', '45243', '45208', '41017', '41091', '45140', '45039']
        if any(zip_code in location for zip_code in tier_1_zips):
            score += 40
        
        return min(score, 100)  # Cap at 100
