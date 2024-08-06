def log_print(*params):
    if len(params) == 1:
        print(params[0])
    elif len(params) == 2:
        sender, message = params
        print(f"[{sender}] {message}")
    else:
        sender, instance, *message = params
        message = " ".join(message)
        print(f"[{sender} ({instance})] {message}")
