import os
import logging
from flask import Flask, jsonify, request, render_template
from coupon_service import CouponService
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize coupon service
coupon_service = CouponService()

@app.route('/')
def index():
    """Render the home page with information about the API."""
    return render_template('index.html')

@app.route('/api/coupons', methods=['GET'])
def get_coupons():
    """Get coupon codes endpoint - returns plain text for easy consumption."""
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    
    try:
        coupon_data = coupon_service.get_coupons(force_refresh=force_refresh)
        
        # Check if client wants JSON or plain text (default to plain text)
        if request.headers.get('Accept') == 'application/json':
            return jsonify(coupon_data)
        else:
            # Format as plain text for easy consumption - just the values
            result = ""
            for coupon in coupon_data:
                result += f"{coupon.get('code', 'No code')}\n"
                result += f"{coupon.get('valid_until', 'Unknown')}\n"
                if len(coupon_data) > 1:  # Only add separator if there are multiple coupons
                    result += "-" * 30 + "\n"
            
            return result, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except Exception as e:
        logger.error(f"Error fetching coupons: {str(e)}")
        
        if request.headers.get('Accept') == 'application/json':
            return jsonify({"error": str(e)}), 500
        else:
            return f"Error: {str(e)}", 500, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/cupon', methods=['GET'])
def show_coupon():
    """Get just the latest coupon code as plain text (for compatibility)."""
    try:
        coupon_data = coupon_service.get_coupons()
        
        if coupon_data and len(coupon_data) > 0:
            # Just return the first code as plain text
            return coupon_data[0].get('code', ''), 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            return '', 404, {'Content-Type': 'text/plain; charset=utf-8'}
    except Exception as e:
        logger.error(f"Error showing coupon: {str(e)}")
        return '', 500, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/api/coupons/status', methods=['GET'])
def get_cache_status():
    """Get the status of the coupon cache."""
    try:
        status = coupon_service.get_cache_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting cache status: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    if request.path.startswith('/api/'):
        return jsonify({"error": "Endpoint not found"}), 404
    return render_template('index.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    if request.path.startswith('/api/'):
        return jsonify({"error": "Server error"}), 500
    return render_template('index.html'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
