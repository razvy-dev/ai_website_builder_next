def save_file(file_path: str, content: str, file_name: str, file_type: str):
    try:
        with open(f"{file_path}/{file_name}.{file_type}", "w") as f:
            f.write(content)
    except Exception as e:
        print(f"Error saving file: {e}")
        return False
    return True