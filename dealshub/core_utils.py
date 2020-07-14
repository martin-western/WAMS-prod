from django.utils import timezone

def check_valid_promotion(promotion_obj):
    return timezone.now() >= promotion_obj.start_time and timezone.now() <= promotion_obj.end_time

def is_voucher_limt_exceeded_for_customer(dealshub_user_obj, voucher_obj):
    if voucher_obj.customer_usage_limit==0:
        return False
    if Order.objects.filter(owner=dealshub_user_obj, voucher=voucher_obj).count()<voucher_obj.customer_usage_limit:
        return False
    return True