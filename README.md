<div align="center">

<!-- Banner -->
<img src="Assets/SmartCity.drawio.png" alt="Smart City Guide Banner" width="100%"/>

<br/>

# 🏙️ Smart City Guide

### *Your intelligent companion to explore, navigate, and discover the city*

<br/>

[![Java](https://img.shields.io/badge/Java-ED8B00?style=for-the-badge&logo=openjdk&logoColor=white)](https://www.java.com/)
[![CLI](https://img.shields.io/badge/Interface-CLI-blue?style=for-the-badge&logo=windowsterminal&logoColor=white)]()
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen?style=for-the-badge&logo=github)](https://github.com/Rajath2005/SmartCityApp/pulls)
[![Contributors](https://img.shields.io/github/contributors/Rajath2005/SmartCityApp?style=for-the-badge&color=orange)](https://github.com/Rajath2005/SmartCityApp/graphs/contributors)
[![Stars](https://img.shields.io/github/stars/Rajath2005/SmartCityApp?style=for-the-badge&color=yellow)](https://github.com/Rajath2005/SmartCityApp/stargazers)
[![Forks](https://img.shields.io/github/forks/Rajath2005/SmartCityApp?style=for-the-badge&color=blue)](https://github.com/Rajath2005/SmartCityApp/network/members)
[![Issues](https://img.shields.io/github/issues/Rajath2005/SmartCityApp?style=for-the-badge&color=red)](https://github.com/Rajath2005/SmartCityApp/issues)
[![Open Source Helpers](https://www.codetriage.com/rajath2005/smartcityapp/badges/users.svg)](https://www.codetriage.com/rajath2005/smartcityapp)
<br/>

[🚀 Get Started](#-getting-started) &nbsp;|&nbsp;
[✨ Features](#-features) &nbsp;|&nbsp;
[🏗️ Project Structure](#️-project-structure) &nbsp;|&nbsp;
[🤝 Contributing](#-contributing) &nbsp;|&nbsp;
[🗺️ Roadmap](#️-roadmap)

</div>

---

## 📌 Overview

**Smart City Guide** is an interactive, console-based Java application that helps residents and tourists **discover, search, and navigate city attractions** with ease. It simulates a smart city environment with a complete role-based system for both regular users and administrators.

Whether you're looking for the best restaurant downtown or managing the city's attraction database as an admin — this app has you covered.

> ⚠️ **Note:** The application currently uses **in-memory storage**. All data resets when the application is restarted. Persistent storage is on the roadmap!

---

## ✨ Features

### 👤 User Features

| Feature | Description |
|---|---|
| 🔐 **Register & Login** | Secure account creation and authentication |
| 🗺️ **View Attractions** | Browse a curated list of city places |
| 🔍 **Search by Category** | Find places by type — Restaurant, Park, Hotel, Museum |
| 📍 **Search by Location** | Find places in specific areas like Downtown or Main Street |
| 🚗 **Navigation** | Simulated access to directions and nearby services |

---

### 🛠️ Admin Features

| Feature | Description |
|---|---|
| ➕ **Add Place** | Add new city attractions to the database |
| ✏️ **Update Place** | Edit details of existing places |
| ❌ **Delete Place** | Remove outdated or incorrect entries |
| 📊 **System Monitoring** | View system logs and user activity (Simulated) |

---

## 🏗️ Project Structure

```
SmartCityGuide/
│
├── 📁 Assets/
│   └── SmartCity.drawio.png        # Architecture diagram
│
├── 📁 src/
│   └── com/
│       └── smartcity/
│           ├── 📁 main/
│           │   └── SmartCityApp.java    # Main entry point & controller
│           └── 📁 model/
│               ├── Place.java           # City place data model
│               └── User.java            # User data model & roles
│
├── README.md
└── .gitignore
```

### 🔑 Key Classes

| Class | Role |
|---|---|
| `SmartCityApp.java` | Main logic, menu flow, and application controller |
| `Place.java` | Represents a city attraction with name, category, and location |
| `User.java` | Manages user data, credentials, and role assignment |

---

## 🚀 Getting Started

### ✅ Prerequisites

Make sure you have the following installed:

- ☕ **Java JDK 8 or higher** → [Download here](https://www.oracle.com/java/technologies/downloads/)
- 💻 **Terminal / IDE** → VS Code, IntelliJ IDEA, or Eclipse

Verify your Java installation:

```bash
java -version
```

---

### ⚡ Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/Rajath2005/SmartCityApp.git

# 2. Navigate into the project
cd SmartCityApp/src

# 3. Compile the application
javac com/smartcity/main/SmartCityApp.java

# 4. Run the application
java com.smartcity.main.SmartCityApp
```

> 💡 **Tip for beginners:** If you're using an IDE like IntelliJ or Eclipse, simply import the project and run `SmartCityApp.java` directly — no terminal needed!

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Language** | Java ☕ |
| **Interface** | Command Line Interface (CLI) |
| **Data Storage** | In-Memory (`HashMap`, `ArrayList`) |
| **Architecture** | Role-Based (User / Admin) |

---

## 🤝 Contributing

We ❤️ contributions — whether you're fixing a bug, adding a feature, or improving docs!

### 🌱 First Time Contributing? Start Here!

New to open source? Don't worry — here's a step-by-step guide:

**Step 1: Fork the repository**

Click the **Fork** button at the top-right of this page.

**Step 2: Clone your fork**

```bash
git clone https://github.com/<your-username>/SmartCityApp.git
cd SmartCityApp
```

**Step 3: Create a new branch**

```bash
git checkout -b feature/your-feature-name
```

> 🧠 Use a descriptive branch name like `feature/add-search-filter` or `fix/login-bug`.

**Step 4: Make your changes**

Write clean, well-commented code. Test it locally before committing.

**Step 5: Commit your work**

```bash
git add .
git commit -m "✨ Add: brief description of your change"
```

**Step 6: Push and open a Pull Request**

```bash
git push origin feature/your-feature-name
```

Then go to your fork on GitHub and click **"Open Pull Request"** 🎉

---

### 📋 Contribution Guidelines

- 🐛 **Bug Reports** → Open an [Issue](https://github.com/Rajath2005/SmartCityApp/issues) with a clear description and steps to reproduce
- 💡 **Feature Requests** → Open an [Issue](https://github.com/Rajath2005/SmartCityApp/issues) with the `enhancement` label
- 📝 **Documentation** → Improvements to README, comments, or Javadocs are always welcome
- ✅ **Good First Issues** → Look for issues tagged [`good first issue`](https://github.com/Rajath2005/SmartCityApp/issues?q=label%3A%22good+first+issue%22) to get started easily

---

## 👥 Contributors

A huge shoutout to everyone who has contributed to this project! 🙌

<a href="https://github.com/Rajath2005/SmartCityApp/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Rajath2005/SmartCityApp" alt="Contributors" />
</a>

*Want to see your face here? [Make a contribution](#-contributing)!*

---

## 🗺️ Roadmap

Here's what's coming next. Feel free to pick one up!

- [ ] 💾 **Persistent Storage** — Save data using file I/O or a database (SQLite/MySQL)
- [ ] 🌐 **REST API** — Expose features via a Spring Boot REST API
- [ ] 🖥️ **GUI Interface** — Build a JavaFX or Swing-based graphical UI
- [ ] ⭐ **Ratings & Reviews** — Let users rate and review places
- [ ] 🗺️ **Map Integration** — Integrate with a maps API for real navigation
- [ ] 🔔 **Notifications** — Alert users about new attractions nearby
- [ ] 🧪 **Unit Tests** — Add JUnit tests for all core classes

> 💡 See something you'd like to build? Check the [Issues tab](https://github.com/Rajath2005/SmartCityApp/issues) or open a new one!

---

## 📊 Project Status

| Status | Description |
|---|---|
| 🟢 **Active** | Actively maintained and open for contributions |
| 🏫 **Education** | Built as part of the Creative Coding Progress series |
| 🤝 **Beginner Friendly** | Great project for Java learners and first-time contributors |

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

You are free to use, modify, and distribute this project with attribution.

---

## ⭐ Support the Project

If you found this project helpful or interesting:

- ⭐ **Star** the repository — it means a lot!
- 🍴 **Fork** it and build your own version
- 🤝 **Contribute** a feature or fix
- 📣 **Share** it with fellow Java learners

---

<div align="center">

**Made with ❤️ by [Rajath2005](https://github.com/Rajath2005) and the community**

*Part of the Creative Coding Progress Series*

<br/>

[![Back to Top](https://img.shields.io/badge/Back%20to%20Top-%E2%AC%86-blue?style=for-the-badge)](#️-smart-city-guide)

</div>
