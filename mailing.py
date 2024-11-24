import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict
import os
import logging
from dotenv import load_dotenv
from jinja2 import Template, Environment, FileSystemLoader
import time

# Configure logging to track all email operations and errors
# Creates a log file that you can review if something goes wrong
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='email_sending.log'
)

# Load environment variables from .env file
load_dotenv()

def validate_email(email: str) -> bool:
    """
    Basic email validation to ensure the email address format is correct.
    You might want to add more sophisticated validation (e.g., specific domain check for @wm.edu)
    
    Args:
        email: The email address to validate
    Returns:
        bool: True if email format is valid, False otherwise
    """
    return '@' in email and '.' in email.split('@')[1]

def send_wrapped_email(user_data: Dict, recipient_email: str) -> bool:
    """
    Send a UC Wrapped email to a single recipient.
    
    Args:
        user_data: Dictionary containing user stats and preferences
        recipient_email: The recipient's email address
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Load config from environment variables
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        port = int(os.getenv('SMTP_PORT', '587'))
        sender_email = os.getenv('SENDER_EMAIL') # uc email
        password = os.getenv('EMAIL_PASSWORD')  # app password

        # Validate that all required environment variables are present
        # This prevents runtime errors from missing credentials
        if not all([smtp_server, port, sender_email, password]):
            logging.error("Missing required environment variables")
            return False

        # Set up Jinja2 environment to look for templates in the current directory
        env = Environment(
            loader=FileSystemLoader('templates')  # Look for templates in a 'templates' folder
        )
        
        # Load the template file
        template = env.get_template('email_template.html')

        # Validate email format before attempting to send
        # This prevents attempts to send to invalid addresses
        if not validate_email(recipient_email):
            logging.error(f"Invalid recipient email: {recipient_email}")
            return False

        # Sanitize user data to prevent template injection and ensure reasonable lengths
        # (I don't think I need this but I'll keep it in anyways)
        sanitized_data = {
            key: str(value).strip()[:1000] if isinstance(value, (str, int, float)) else value
            for key, value in user_data.items()
            # strip() removes leading/trailing whitespace
            # [:1000] ensures no value is longer than 1000 characters
        }

        # Create message container for HTML email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Your Fall 2024 Union Central Wrapped!"
        msg['From'] = sender_email
        msg['To'] = recipient_email

        # Render HTML email body with sanitized data
        html_body = template.render(**sanitized_data)
        
        # Create and attach HTML part
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)

        # Use 'with' statement for proper cleanup of SMTP connection
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()  # Enable TLS encryption
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
            
        # Log successful sending for audit purposes
        logging.info(f"Successfully sent email to {recipient_email}")
        return True

    except Exception as e:
        # Log errors for debugging
        logging.error(f"Error sending email to {recipient_email}: {str(e)}")
        return False

def batch_send_emails(user_data_list: list, batch_size: int = 50) -> Dict:
    """
    Send emails in batches to prevent overwhelming the SMTP server and
    to maintain better control over the sending process.
    
    Args:
        user_data_list: List of dictionaries containing user data
        batch_size: Number of emails to send in each batch
    Returns:
        Dict: Statistics about successful and failed email sends
    """
    results = {"successful": 0, "failed": 0, "total": len(user_data_list)}
    
    # Process emails in batches to prevent server overload
    for i in range(0, len(user_data_list), batch_size):
        batch = user_data_list[i:i + batch_size]
        for user_data in batch:
            time.sleep(1)  # Delay to prevent rate limiting
            if send_wrapped_email(user_data, user_data.get('email')):
                results["successful"] += 1
            else:
                results["failed"] += 1
        time.sleep(10)  # Delay between batches to prevent rate limiting
                
    return results

# Example usage and testing code
if __name__ == "__main__":
    # Test data for a single email
    # In production, this would come from your database or data processing script
    test_data = {
        "name": "Carlo",
        "email": "cjmehegan@wm.edu",
        "total_rentals": 8,
        "total_users": 1000,
        "total_rental_ranking": "42nd",
        #table games - favorite table game
        "fav_rental_type": "pool table",
        "fav_type_users": 300,
        "fav_rental_type_count": 5,
        "fav_rental_type_ranking": "15th",
        "fav_rental_type_duration_average": 45,
        "fav_rental_type_duration_total": 225,
        "fav_table": "Table 2",
        #video games - favorite console
        "fav_table_count": 3,
        "fav_console": "PS5",
        "fav_console_count": 2,
        "fav_console_ranking": "7th",
        "fav_console_users": 500,
        "fav_console_duration_average": 120,
        "fav_console_duration_total": 240,
        #video games - favorite games
        "top_games": [
            {
                "name": "Super Smash Bros Ultimate",
                "total_minutes": 240,
                "total_rentals": 5
            },
            {
                "name": "Mario Kart 8",
                "total_minutes": 180,
                "total_rentals": 4
            },
            {
                "name": "FIFA 23",
                "total_minutes": 150,
                "total_rentals": 3
            },
            {
                "name": "NBA 2K22",
                "total_minutes": 90,
                "total_rentals": 2
            }
        ],
        #board games - favorite board game
        "fav_board": "Catan",
        "fav_board_count": 2,
        "fav_board_ranking": "3rd",
        "fav_board_users": 12,
        "fav_board_duration_average": 120,
        "fav_board_duration_total": 240
    }
    
    # test with a single email first
    # Use environment variable for test email to keep it secure
    test_result = send_wrapped_email(test_data, os.getenv('TEST_EMAIL'))
    print(f"Test email {'sent successfully' if test_result else 'failed'}")