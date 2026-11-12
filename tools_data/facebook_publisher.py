def format_facebook_post(message: str, call_to_action_url: str = None) -> dict:
    return {'message': message.strip(), 'link': call_to_action_url, 'published': True}
