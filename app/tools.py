def search_web(query : str):
    return {
        "status" : "success",
        "tool": "search_web",
        "result" : f"search result for search {query}"
    }


def send_email(target : str):
    return {
        "status" : "success",
        "tool" : "send_email",
        "result" : f"email sent to {target}"
    }


def delete_file(target : str):
    return {
        "status" : "success",
        "tool" : "delete_file",
        "result" : f"file {target} has been deleted"
    }


def transfer_money(target : str, amount : float):
    return {
        "status" : "success",
        "tool" : "transfer_money",
        "result" : f"amount {amount} has been transferred to {target}"
    }

