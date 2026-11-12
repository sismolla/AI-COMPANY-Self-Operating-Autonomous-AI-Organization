def format_linkedin_post(text: str, hashtags: list = None, link_url: str = None) -> dict:
    tags = ' '.join([f'#{h.replace("#", "")}' for h in (hashtags or [])])
    body = f'{text.strip()}\n\n{tags}'.strip() if tags else text.strip()
    return {'body': body, 'link_url': link_url, 'visibility': 'PUBLIC'}
