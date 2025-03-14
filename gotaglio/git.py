# Uncomment the following code for testing the case where git is not available.
# import os
# original_path = os.environ['PATH']
# os.environ['PATH'] = os.pathsep.join([p for p in original_path.split(os.pathsep) if 'Git\\cmd' not in p])

try:
    from git import Repo
except ImportError:
    print("WARNING: The git command cannot be found. Runlog will not record the git sha and diffs.")

def get_git_sha(repo_path="."):
    try:
        repo = Repo(repo_path)
        sha = repo.head.commit.hexsha
        return sha
    except Exception as e:
        # print(f"Error: {e}")
        return None


def get_current_edits(repo_path="."):
    repo = Repo(repo_path)
    edits = {"modified": [], "added": [], "deleted": [], "untracked": [], "renamed": []}

    # Get modified, added, deleted, and renamed files
    for item in repo.index.diff(None):
        if item.change_type == "M":
            edits["modified"].append(item.a_path)
        elif item.change_type == "A":
            edits["added"].append(item.a_path)
        elif item.change_type == "D":
            edits["deleted"].append(item.a_path)
        elif item.change_type == "R":
            edits["renamed"].append(f"{item.a_path} -> {item.b_path}")

    # Get untracked files
    edits["untracked"] = repo.untracked_files

    return edits
