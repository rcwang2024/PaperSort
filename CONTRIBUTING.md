# Contributing to PaperSort

Thank you for your interest in contributing! To ensure the app remains stable and high-quality, please follow these guidelines.

## 🚨 Golden Rule: Don't Break the App

**Every time we add a feature without proper testing, something breaks.**

This document exists to prevent that cycle. Please read it carefully.

## Required Reading

Before making ANY changes, read these documents in order:

1. **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development workflow, testing requirements, common pitfalls
2. **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design, components, critical code sections
3. **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Issues we've already solved (don't repeat them)
4. **[TESTING.md](TESTING.md)** - Testing infrastructure and how to use it

**Not optional.** These docs contain critical information about what NOT to do.

## Pre-Contribution Checklist

- [ ] I have read DEVELOPMENT.md, ARCHITECTURE.md, and TROUBLESHOOTING.md
- [ ] I understand the component architecture
- [ ] I know which code sections are critical (ARCHITECTURE.md)
- [ ] I understand the testing requirements
- [ ] I have set up the development environment
- [ ] All existing tests pass on my machine

## Development Workflow

### 1. Setup

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/PaperSort.git
cd PaperSort

# Install dependencies
npm install
cd frontend && npm install && cd ..
cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && cd ..

# Verify setup
npm run test:all  # All tests must pass
```

### 2. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 3. Before Making Changes

```bash
# Run tests to establish baseline
npm run test:all

# If tests fail, fix them BEFORE making your changes
```

### 4. Make Your Changes

**For backend changes:**
- Modify code in `backend/app/`
- Add/update tests in `backend/tests/`
- Update documentation if needed

**For frontend changes:**
- Modify code in `frontend/src/`
- Add/update tests in `frontend/src/tests/`
- Update types if needed

**For Electron changes:**
- Modify `electron/main.js` carefully (see ARCHITECTURE.md for critical sections)
- Test thoroughly in both dev and production modes

### 5. Write Tests

**Every change must include tests:**

- New feature? Add tests that verify it works
- Bug fix? Add test that would have caught the bug
- Refactoring? Ensure existing tests still pass

**Test locations:**
- Backend unit tests: `backend/tests/unit/`
- Backend integration tests: `backend/tests/integration/`
- Frontend tests: `frontend/src/tests/`
- E2E tests: `frontend/e2e/`

### 6. Run Tests

```bash
# Run full test suite
npm run test:all

# Or run individually
cd backend && pytest -v
cd frontend && npm test
cd frontend && npm run test:e2e
```

**All tests MUST pass before committing.**

### 7. Manual Testing

**Always test manually:**

```bash
# Development mode
npm run electron:dev

# Test your feature
# Try edge cases
# Try to break it
```

**For significant changes, test production build:**

```bash
npm run build
open dist-installer/PaperSort-2.0.0-arm64.dmg
# Install and test
```

### 8. Commit

**Pre-commit hook will run tests automatically.**

```bash
git add <files>
git commit -m "feat: your feature description

- What changed
- Why it changed
- How it was tested

Tested:
- Unit tests: passing
- Integration tests: passing
- Manual testing: completed in dev and prod"
```

**Commit message format:**
- `feat:` New feature
- `fix:` Bug fix
- `refactor:` Code restructuring
- `test:` Adding/updating tests
- `docs:` Documentation
- `chore:` Maintenance

### 9. Push and Create PR

```bash
git push origin feature/your-feature-name
```

**In the PR description, include:**
1. What problem does this solve?
2. How does it solve it?
3. What tests were added/updated?
4. Screenshots (if UI changes)
5. Testing checklist:
   - [ ] All unit tests pass
   - [ ] All integration tests pass
   - [ ] Manual testing in dev mode
   - [ ] Manual testing in production build (for significant changes)

## What NOT to Do

**Read TROUBLESHOOTING.md for full list.** Here are the most critical:

### ❌ DON'T commit with failing tests
**This is the #1 cause of breaking the app.**

### ❌ DON'T skip manual testing
**Tests don't catch everything, especially UI/UX issues.**

### ❌ DON'T modify critical code sections without understanding them
**Read ARCHITECTURE.md to identify critical sections:**
- Port conflict resolution (`electron/main.js:43-91`)
- Backend launching (`electron/main.js:125-159`)
- Dependency checking (`electron/main.js:300-450`)
- Clustering algorithm (`backend/app/services/paper_organizer.py:463-605`)

### ❌ DON'T use PyInstaller bundled exe
**Use `run_backend.sh` (Python script). Bundled exe doesn't work with uvicorn on macOS.**

### ❌ DON'T use --noconsole for servers
**Server applications need --console mode for stdio.**

### ❌ DON'T remove marker file logic
**This prevents endless dependency check loops.**

### ❌ DON'T change clustering without testing on 500+ papers
**Small datasets don't reveal imbalance issues.**

## Code Review Checklist

**Reviewers should verify:**

- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated if needed
- [ ] No debug code left (console.log, print statements)
- [ ] Code follows existing patterns
- [ ] No breaking changes to critical sections
- [ ] Manual testing completed
- [ ] Commit messages are clear

## Questions?

- Check **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** for common issues
- Check **[DEVELOPMENT.md](DEVELOPMENT.md)** for development workflow
- Check **[ARCHITECTURE.md](ARCHITECTURE.md)** for system design
- Open an issue if you need clarification

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
