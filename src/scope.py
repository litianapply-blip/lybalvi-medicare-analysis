"""Geographic scope for CMS retrieval."""

US_STATES = """
AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA
ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR
PA RI SC SD TN TX UT VT VA WA WV WI WY
""".split()


def allowed_states(scope):
    if scope == "US":
        return US_STATES
    if scope in US_STATES:
        return [scope]
    raise ValueError(f"Unsupported geographic scope: {scope}")


def state_filter_params(scope):
    states = allowed_states(scope)
    if len(states) == 1:
        return {"filter[Prscrbr_State_Abrvtn]": states[0]}
    return {
        "filter[state][condition][path]": "Prscrbr_State_Abrvtn",
        "filter[state][condition][operator]": "IN",
        "filter[state][condition][value][]": states,
    }
