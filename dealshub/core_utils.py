from django.utils import timezone
import requests
import sys
import logging

logger = logging.getLogger(__name__)

def check_valid_promotion(promotion_obj):
    return timezone.now() >= promotion_obj.start_time and timezone.now() <= promotion_obj.end_time

def remove_stopwords_core(string):
    words = string.strip().split(" ")
    stopwords = ["i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"]
    cleaned_words = []
    for word in words:
        if word not in stopwords:
            cleaned_words.append(word)
    cleaned_string = " ".join(cleaned_words)
    return cleaned_string

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def refresh_section_cache(location_group_uuid):
    try:
        url = "https://qa.omnycomm.com:8028/dealshub/fetch-dealshub-admin-sections/"
        data = {
            "isDealshub": True,
            "limit": True,
            "locationGroupUuid": location_group_uuid,
            "resolution": "high",
            "isBot": True
        }
        r = requests.post(url=url, json=data)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("refresh_section_cache: %s at %s", e, str(exc_tb.tb_lineno)) 