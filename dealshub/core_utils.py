from django.utils import timezone

def check_valid_promotion(promotion_obj):
    return timezone.now() >= promotion_obj.start_time and timezone.now() <= promotion_obj.end_time