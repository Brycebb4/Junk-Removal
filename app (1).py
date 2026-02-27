# CincyJunkBot - Flask Web Application
# Junk Removal Lead Generation System for Cincinnati/Northern Kentucky

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import threading
import time
import json
from datetime import datetime
import os

from bot.scraper import CincinnatiCraigslistScraper
from bot.filters import LeadFilter
from bot.notifier import NotificationManager
from bot.database import LeadDatabase

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'cincy-junk-bot-secret-key-2024'
app.config['JSON_SORT_KEYS'] = False

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize components
db = LeadDatabase()
lead_filter = LeadFilter()
notifier = NotificationManager()
scraper = CincinnatiCraigslistScraper()

# Bot control variables
bot_running = False
bot_thread = None

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/leads')
def get_leads():
    """Get all leads with optional filters"""
    status = request.args.get('status', 'all')
    source = request.args.get('source', 'all')
    limit = int(request.args.get('limit', 50))

    leads = db.get_leads(status=status, source=source, limit=limit)
    return jsonify({
        'success': True,
        'leads': leads,
        'count': len(leads)
    })

@app.route('/api/leads/<lead_id>', methods=['GET'])
def get_lead(lead_id):
    """Get a specific lead by ID"""
    lead = db.get_lead(lead_id)
    if lead:
        return jsonify({'success': True, 'lead': lead})
    return jsonify({'success': False, 'error': 'Lead not found'}), 404

@app.route('/api/leads/<lead_id>/status', methods=['PUT'])
def update_lead_status(lead_id):
    """Update lead status"""
    data = request.get_json()
    new_status = data.get('status')

    if db.update_status(lead_id, new_status):
        # Emit update to all connected clients
        socketio.emit('lead_updated', {'lead_id': lead_id, 'status': new_status})
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Failed to update'}), 400

@app.route('/api/leads/<lead_id>/notes', methods=['PUT'])
def update_lead_notes(lead_id):
    """Update lead notes"""
    data = request.get_json()
    notes = data.get('notes', '')

    if db.update_notes(lead_id, notes):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Failed to update'}), 400

@app.route('/api/stats')
def get_stats():
    """Get dashboard statistics"""
    stats = db.get_stats()
    return jsonify({'success': True, 'stats': stats})

@app.route('/api/bot/status')
def bot_status():
    """Get bot running status"""
    global bot_running
    return jsonify({
        'success': True,
        'running': bot_running,
        'last_check': scraper.last_check_time if hasattr(scraper, 'last_check_time') else None
    })

@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    """Start the lead generation bot"""
    global bot_running, bot_thread

    if not bot_running:
        bot_running = True
        bot_thread = threading.Thread(target=bot_worker, daemon=True)
        bot_thread.start()
        return jsonify({'success': True, 'message': 'Bot started'})
    return jsonify({'success': False, 'error': 'Bot already running'}), 400

@app.route('/api/bot/stop', methods=['POST'])
def stop_bot():
    """Stop the lead generation bot"""
    global bot_running

    if bot_running:
        bot_running = False
        return jsonify({'success': True, 'message': 'Bot stopped'})
    return jsonify({'success': False, 'error': 'Bot not running'}), 400

@app.route('/api/templates')
def get_templates():
    """Get quick response templates"""
    templates = [
        {
            'id': 1,
            'name': 'Quick Quote',
            'content': 'Hi! I saw your post about {service} in {location}. I can help with this today! Can you tell me more about what needs to be removed?',
            'type': 'sms'
        },
        {
            'id': 2,
            'name': 'Availability Check',
            'content': 'Hello! Interested in your junk removal needs in {location}. I have availability this week. What days work for you?',
            'type': 'sms'
        },
        {
            'id': 3,
            'name': 'Same Day Service',
            'content': 'Hey! I can do same-day service for your {service} in {location}. I have a truck available now. Would you like me to come give you a quote?',
            'type': 'sms'
        },
        {
            'id': 4,
            'name': 'Professional Inquiry',
            'content': 'Hi there, I came across your listing for {service}. I run a professional junk removal service in the Cincinnati area. Would you like a free estimate?',
            'type': 'email'
        }
    ]
    return jsonify({'success': True, 'templates': templates})

@app.route('/api/export', methods=['GET'])
def export_leads():
    """Export leads to CSV format"""
    leads = db.get_leads(status='all', limit=1000)

    csv_data = "ID,Source,Title,Location,Estimated Value,Status,Posted Time,Discovered Time\n"
    for lead in leads:
        csv_data += f"{lead['id']},{lead['source']},{lead['title']},{lead['location']},{lead['estimated_value']},{lead['status']},{lead['posted_time']},{lead['discovered_time']}\n"

    return csv_data, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=leads.csv'
    }

def bot_worker():
    """Background worker that scrapes for leads"""
    global bot_running

    check_interval = 60  # Check every 60 seconds

    while bot_running:
        try:
            # Scrape Cincinnati Craigslist
            new_leads = scraper.fetch_leads()

            for raw_lead in new_leads:
                # Filter the lead
                filtered_lead = lead_filter.process(raw_lead)

                if filtered_lead:
                    # Check for duplicates
                    if not db.is_duplicate(filtered_lead['source_url']):
                        # Save to database
                        lead_id = db.add_lead(filtered_lead)
                        filtered_lead['id'] = lead_id

                        # Emit to connected clients
                        socketio.emit('new_lead', filtered_lead)

                        # Send notification for hot leads
                        if filtered_lead.get('priority_score', 0) >= 75:
                            notifier.send_alert(filtered_lead)

            # Update last check time
            scraper.last_check_time = datetime.now().isoformat()

        except Exception as e:
            print(f"Bot error: {e}")

        # Sleep before next check
        time.sleep(check_interval)

# Demo data for initial testing
def init_demo_data():
    """Initialize with some demo leads for testing"""
    demo_leads = [
        {
            'source': 'craigslist',
            'source_url': 'https://cincinnati.craigslist.org/hsh/d/mason-garage-cleanout-full/123456.html',
            'title': 'Garage Cleanout - Full House Move Out',
            'description': 'Moving out of my house in Mason. Need help cleaning out the garage, basement, and attic. Everything must go. Heavy furniture, boxes, old appliances. Looking for someone who can take everything.',
            'location': 'Mason, OH 45040',
            'keywords_detected': ['garage cleanout', 'full house', 'basement', 'attic', 'heavy furniture', 'appliances'],
            'estimated_value': '$300-$500',
            'priority_score': 92,
            'posted_time': datetime.now().isoformat(),
            'status': 'new'
        },
        {
            'source': 'craigslist',
            'source_url': 'https://cincinnati.craigslist.org/hsh/d/cincinnati-estate-cleanout/234567.html',
            'title': 'Estate Cleanout Needed - Professional Service',
            'description': 'Need junk removal service for estate cleanout. 4 bedroom home with furniture, clothing, and household items. Second floor has heavy furniture that needs to be carried down. Immediate availability preferred.',
            'location': 'Hyde Park, Cincinnati OH 45208',
            'keywords_detected': ['estate cleanout', 'furniture', 'heavy', 'immediate'],
            'estimated_value': '$500+',
            'priority_score': 88,
            'posted_time': datetime.now().isoformat(),
            'status': 'contacted'
        },
        {
            'source': 'facebook',
            'source_url': 'https://facebook.com/marketplace/123456',
            'title': 'Hot Tub Removal - Need Help ASAP',
            'description': 'Removing an old hot tub from backyard. Need someone with a truck and trailer. It\'s in the backyard, need to go through gate. Will pay well for quick service.',
            'location': 'Union, KY 41091',
            'keywords_detected': ['hot tub removal', 'truck', 'trailer', 'backyard'],
            'estimated_value': '$175-$300',
            'priority_score': 78,
            'posted_time': datetime.now().isoformat(),
            'status': 'new'
        },
        {
            'source': 'craigslist',
            'source_url': 'https://cincinnati.craigslist.org/hsh/d/covington-construction-debris/345678.html',
            'title': 'Construction Debris Removal',
            'description': 'Just finished a renovation project. Have about a truck load of construction debris - drywall, lumber, flooring materials. Need someone to haul it away.',
            'location': 'Covington, KY 41011',
            'keywords_detected': ['construction debris', 'renovation', 'truck load'],
            'estimated_value': '$175-$300',
            'priority_score': 71,
            'posted_time': datetime.now().isoformat(),
            'status': 'quoted'
        },
        {
            'source': 'nextdoor',
            'source_url': 'https://nextdoor.com/123456',
            'title': 'Need junk removal for shed demo',
            'description': 'Looking for someone to demolish and remove an old shed in my backyard. About 10x12 wooden shed. Can handle removal?',
            'location': 'Maineville, OH 45039',
            'keywords_detected': ['shed demo', 'demolish', 'wooden'],
            'estimated_value': '$300-$500',
            'priority_score': 82,
            'posted_time': datetime.now().isoformat(),
            'status': 'new'
        }
    ]

    # Add demo leads if database is empty
    existing = db.get_leads(limit=1)
    if not existing:
        for lead in demo_leads:
            db.add_lead(lead)

# Initialize demo data on startup
with app.app_context():
    init_demo_data()

if __name__ == '__main__':
    # Run with SocketIO support
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
