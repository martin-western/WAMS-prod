def check_valid_promotion(time,promotion):
    """
    Checks if a promotion is valid or not based on time 
    """
    return time >= promotion.start_time and time <=promotion.end_time