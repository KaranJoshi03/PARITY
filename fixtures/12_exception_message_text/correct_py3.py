def get_exc_msg():
    try:
        raise ValueError("invalid input")
    except ValueError as e:
        return bool(str(e))  # Use str(e) instead of e.message

if __name__ == "__main__":
    print(get_exc_msg())
