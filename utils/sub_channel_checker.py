required_channel_ids = [-1001399964263, -1002147509062]


def is_user_subscribed(user_id, bot):
    """Проверяет, подписан ли пользователь на все каналы из списка по ID"""
    for channel_id in required_channel_ids:
        try:
            # Получаем статус пользователя в канале
            status = bot.get_chat_member(channel_id, user_id).status
            # Статусы 'member', 'administrator', 'creator' означают подписку
            if status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            print(f"Ошибка проверки подписки на канал {channel_id}: {e}")
            return False
    return True
