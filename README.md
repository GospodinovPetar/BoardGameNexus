# BoardGame Nexus

BoardGame Nexus is a web application designed to facilitate the discovery of board games and the organization of board game events. It provides a platform for users to browse an extensive catalog of games, manage gaming events, and connect with other enthusiasts.

## Features

*   **Event Management:** Create, edit, delete, and join local board gaming events.
*   **Game Catalog:** Explore a comprehensive database of board games. Users can add new titles, edit game details, and search for specific games.
*   **Intuitive User Interface:** A clean and visually appealing design that ensures ease of navigation.
*   **Star Rating System:** Games can be rated using an interactive star system, offering quick insights into their popularity or quality.
*   **Admin Panel:** Advanced administrative controls for managing games and events, including filtering and sorting capabilities for all fields.
*   **In-App Notifications:** Receive important messages and confirmations directly within the application.
*   **Responsive Design:** The application is fully responsive, providing an optimal experience across various devices, from desktops to mobile phones.
*   **Filtering and Sorting:** Advanced filtering and sorting options for both games and events to help users find exactly what they are looking for.

## Technologies Used

*   **Django:** A high-level Python Web framework for rapid and secure backend development.
*   **Bootstrap 5:** A modern CSS framework for building responsive and elegant frontend designs.
*   **Crispy Forms:** Enhances Django forms with clean and aesthetically pleasing rendering.
*   **PostgreSQL:** A powerful, open-source object-relational database system used for data storage.
*   **Python:** The primary programming language powering the application.

## Setup Guide

To get BoardGame Nexus up and running on your local machine, follow these steps:

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-username/BoardGameNexus.git
    cd BoardGameNexus
    ```

2.  **Create and Activate a Virtual Environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # For Linux/macOS
    # .venv\Scripts\activate   # For Windows
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Database Configuration (PostgreSQL):**
    *   Ensure you have PostgreSQL installed and running.
    *   Create a new database (e.g., named `nexus`).
    *   Update the database settings in `BoardGameNexus/settings.py` (specifically the `DATABASES` section) to match your PostgreSQL credentials (NAME, USER, PASSWORD, HOST, PORT).

5.  **Run Database Migrations:**
    ```bash
    python manage.py migrate
    ```

6.  **Create a Superuser (for Admin Panel access):**
    ```bash
    python manage.py createsuperuser
    ```

7.  **Run the Development Server:**
    ```bash
    python manage.py runserver
    ```

Open your web browser and navigate to `http://127.0.0.1:8000/` to access the application.

## Contributing

Contributions to BoardGame Nexus are welcome! If you find a bug, have an idea for a new feature, or want to contribute code, please open an issue or submit a pull request.

## License

This project is licensed under the MIT License. Refer to the `LICENSE` file for more details.

## Contact

For any questions, suggestions, or feedback, please contact us at [your_email@example.com].
