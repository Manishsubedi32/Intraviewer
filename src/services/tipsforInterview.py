from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import random
from pypdf import PdfReader
import re

class TipsForInterviewService:

    @staticmethod
    def get_random_tips(token: HTTPAuthorizationCredentials):
        file_path = "/Users/manishsubedi/Documents/coding/Intraviewer/backend/100_hacks.pdf"
        try:
            reader = PdfReader(file_path)
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text() + "\n"
            
            # --- Parsing Logic ---
            lines = full_text.split('\n')
            
            topics = {}
            current_topic = "General Tips" # Default topic
            
            # Regex to find "1. Tip Text", "11. Tip Text" etc.
            tip_pattern = re.compile(r'^\s*(\d+)\.\s+(.*)')
            
            # Icons or headers from your PDF content
            topic_indicators = [
                "Automatic Zoom", 
                "Mindset & Psychology", 
                "Pre-Interview Recon", 
                "The Virtual Setup", 
                "Answering Strategy & Delivery", 
                "Technical & Engineering Interviews", 
                "Academic & Advanced Degree Hacks", 
                "Body Language & Non-Verbal Data"
            ]

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # 1. Check for Topic Header
                # If line matches one of our known topics loosely
                is_header = False
                for indicator in topic_indicators:
                    if indicator in line:
                        current_topic = line # Use the actual line as the topic name
                        if current_topic not in topics:
                            topics[current_topic] = []
                        is_header = True
                        break
                
                if is_header:
                    continue

                # 2. Check for Tip (e.g., "1. The Colleague Frame...")
                match = tip_pattern.match(line)
                if match:
                    tip_number = match.group(1)
                    tip_content = match.group(2)
                    
                    if current_topic not in topics:
                        topics[current_topic] = []
                        
                    topics[current_topic].append({
                        "id": tip_number,
                        "tip": tip_content
                    })
                else:
                    # 3. Handle multi-line tips
                    # If line is NOT a header and NOT a new tip, append to previous tip
                    if current_topic in topics and topics[current_topic]:
                        last_tip = topics[current_topic][-1]
                        # Append with space
                        last_tip['tip'] += " " + line

            # --- Select One Random Tip ---
            all_topics = list(topics.keys())
            if not all_topics:
                 return {"topic": "General", "tip_number": "0", "tip_text": "No tips found in PDF."}
            
            # Pick a random topic
            random_topic_name = random.choice(all_topics)
            tips_in_topic = topics[random_topic_name]
            
            if not tips_in_topic:
                 return {"topic": random_topic_name, "tip_number": "0", "tip_text": "No specific tips found in this section."}

            # Pick a random tip from that topic
            random_tip = random.choice(tips_in_topic)

            return {
                "topic": random_topic_name,
                "tip_number": random_tip['id'],
                "tip_text": random_tip['tip']
            }

        except Exception as e:
            print(f"Error parsing PDF: {e}")
            raise HTTPException(status_code=500, detail=f"Error reading PDF file: {str(e)}")
