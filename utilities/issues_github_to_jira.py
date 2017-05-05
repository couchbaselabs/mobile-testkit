import requests


# Github credentials
USERNAME = "raghusarangapani"
PASSWORD = "?Rag03arc!"

# Project you want to export issues from
USER = "raghusarangapani"
PROJECT = "couchbase/sync_gateway"

# Github API for issues
GITHUB_API = "https://api.github.com"

CSV_FILE = "/Users/raghu.sarangapani/Desktop/issues.csv"

priority_map = {
    "P1: high": "Blocker",
    "P2: medium": "Critical",
    "P3: low": "Minor"
}

user_map = {
    "raghusarangapani": "raghu.sarangapani",
    "sethrosetter": "Seth.Rosetter",
    "adamcfraser": "Adam.Fraser",
    "tleyden": "tleyden",
    "ajres": "areslan",
    "andreibaranouski": "andrei",
    "snej": "jens",
    "hideki": "hideki"
}

s = requests.Session()
s.auth = (USERNAME, PASSWORD)
payload = {"labels": "bug", "filter": "all", "state": "all"}
URL = "{}/repos/{}/issues".format(GITHUB_API, PROJECT)
r = s.get(URL, params=payload)
issues_json = r.json()
print "Found {} issues".format(len(issues_json))
headers = ['Issue Key', 'Type', 'Component', 'Description', 'GithubURL', 'Date Created', 'Date Modified', 'Status', 'Reporter',
           'Assignee', 'Priority', 'FixVersion', 'Summary']

for i in issues_json:
    reporter = i["user"]["login"]

    if reporter != USER:
        continue

    component = PROJECT.split("/")[1]
    comments_array = []

    if i["assignee"]:
        assignee = i["assignee"]["login"]

    github_url = i["html_url"]
    Summary = i["title"]
    created = i["created_at"]
    created = created.replace("T", " ")
    created = created.replace("Z", " ")

    modified = i["updated_at"]
    modified = modified.replace("T", " ")
    modified = modified.replace("Z", " ")

    priority = ""
    for j in i["labels"]:
        if "P" in j["name"]:
            priority = j["name"]
    status = i["state"]
    body = i["body"]
    body = body.replace("\"", "\"\"")
    body = body.replace("###", "-")
    milestone = ""
    if i["milestone"]:
        milestone = i["milestone"]["title"]

    # Check for comments
    comments = i["comments"]
    comments_url = ""
    if comments > 0:
        comments_url = i["comments_url"]

    # Get all the comments
    c = requests.Session()
    c.auth = (USERNAME, PASSWORD)
    cr = c.get(comments_url)
    comments_json = cr.json()

    for j in comments_json:
        headers.append('Comment')
        commenter = user_map[j["user"]["login"]]
        comment_created = j["created_at"]
        comment_created = comment_created.replace("T", " ")
        comment_created = comment_created.replace("Z", " ")
        comment_body = j["body"]
        comment_body = comment_body.replace("'", "")
        comment = ";".join(list([comment_created, commenter, comment_body]))
        comments_array.append(comment)

    f = open(CSV_FILE, "w")
    f.write(",".join(headers))
    f.write("\n")
    f.write("\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\"".format("CBL-61", "Bug", component, body, github_url, created, modified, status, user_map[reporter], user_map[assignee], priority_map[priority], milestone, Summary, ",".join(comments_array)))
    f.close()

    milestone = ""
    number = ""
    Summary = ""
    created = ""
    modified = ""
    priority = ""
    status = ""
    reporter = ""
    component = ""
    body = ""
    github_url = ""
    comments_array = ""
