code = '''def combinations(n, r):
    if r == 0 or n == r:
        return 1
    return combinations(n - 1, r - 1) + combinations(n - 1, r)

print("Number of ways to choose 3 black marbles out of 12:")
print(combinations(12, 3))'''

exec(code)