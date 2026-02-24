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
                    
                    # Store current tip
                    topics[current_topic].append({
                        "id": tip_number,
                        "tip": tip_content
                    })
                    
                    # Special check: Sometimes multiple short tips are on one line in PDF (e.g. "90. Next Steps...")
                    # We check if 'tip_content' ITSELF contains another numbered tip like "90. Next Steps..."
                    secondary_match = tip_pattern.search(tip_content)
                    if secondary_match:
                        # Find where the second tip starts
                        start_idx = secondary_match.start()
                        
                        # 1. Update the FIRST tip to end before the second one starts
                        first_tip_text = tip_content[:start_idx].strip()
                        topics[current_topic][-1]["tip"] = first_tip_text
                        
                        # 2. Add the SECOND tip as a new entry
                        second_tip_number = secondary_match.group(1)
                        second_tip_text = secondary_match.group(2)
                        
                        topics[current_topic].append({
                            "id": second_tip_number,
                            "tip": second_tip_text
                        })
                else:
                    # 3. Handle multi-line tips
                    # If line is NOT a header and NOT a new tip, append to previous tip
                    if current_topic in topics and topics[current_topic]:
                        last_tip = topics[current_topic][-1]
                        
                        # Clean up formatting: if we accidentally append a section header at end
                        # Ex: "10. End on a High Note... 🏁 Closing & Follow-Up"
                        # We try to remove known topic headers if they appear at the END of a tip
                        for indicator in topic_indicators:
                           if indicator in line:
                               line = line.replace(indicator, "").strip()

                        # Only append if it looks like sentence continuation
                        if line:
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
