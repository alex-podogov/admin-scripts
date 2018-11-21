base:
    '*':
        - secret
dev:
    '*':
        - env.dev.access
lab:
    '*':
        - env.lab.password
