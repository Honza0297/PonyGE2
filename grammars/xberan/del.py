with open("original-PPA-Grammar.txt") as f:
    for line in f:
        if line.strip():
            print("\\begin{flalign}")
            print("    "+line.strip())
            print("\\end{flalign}")
