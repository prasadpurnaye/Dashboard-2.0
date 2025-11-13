# Dashboard 2.0 🎯

A comprehensive real-time monitoring dashboard built with FastAPI, InfluxDB3, and modern responsive web technologies. Features multi-gauge monitoring, VM telemetry collection, and memory dump management with a fully mobile-responsive interface.

## ✨ Features

### Core Monitoring
- **8 Real-time Gauges**: Temperature readings (0-90°C) with 5 decimal precision
- **Live Data Updates**: Auto-refresh every 5 seconds
- **InfluxDB3 Integration**: Efficient time-series data storage and querying
- **Multi-VM Support**: Monitor multiple virtual machines simultaneously

### Advanced Features
- **Telemetry Collection**: Background VM statistics collection
- **Memory Dump Management**: Trigger, track, and analyze VM memory dumps
- **Activity Logging**: Real-time activity tracking and updates
- **Data Export**: Export records to CSV format
- **Search & Filtering**: Advanced filtering and search capabilities

### Mobile Experience
- **Fully Responsive**: Works seamlessly on desktop, tablet, and mobile
- **Hamburger Navigation**: Collapsible menu for mobile devices
- **Touch-Optimized**: 44px+ touch targets for easy mobile interaction
- **Smooth Animations**: GPU-accelerated CSS animations

### Accessibility
- **WCAG 2.1 Compliant**: Full accessibility support
- **Screen Reader Support**: ARIA labels and semantic HTML
- **Keyboard Navigation**: Complete keyboard accessibility
- **High Contrast**: WCAG AA color contrast compliance

## 📋 Project Structure

## Project Structure
```
dashboard-2.0
├── src
│   ├── main.py              # Entry point of the FastAPI application
│   ├── config.py            # Configuration settings for the application
│   ├── database
│   │   ├── __init__.py      # Initializer for the database package
│   │   └── influxdb.py      # Functions to interact with InfluxDB 3
│   ├── api
│   │   ├── __init__.py      # Initializer for the API package
│   │   └── routes.py        # API routes for fetching gauge data
│   ├── models
│   │   ├── __init__.py      # Initializer for the models package
│   │   └── gauge.py         # Gauge model definition
│   └── utils
│       ├── __init__.py      # Initializer for the utils package
│       └── helpers.py       # Utility functions for the application
├── static
│   ├── css
│   │   └── style.css        # CSS styles for the dashboard interface
│   └── js
│       └── dashboard.js      # JavaScript code for rendering gauges
├── templates
│   └── index.html           # Main HTML template for the dashboard
├── requirements.txt          # Project dependencies
├── .env                      # Environment variables
└── README.md                 # Project documentation
```

## Setup Instructions
1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd dashboard-2.0
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   Create a `.env` file in the root directory and add your database credentials and other necessary configurations.

5. **Run the application**:
   ```bash
   uvicorn src.main:app --reload
   ```

6. **Access the dashboard**:
   Open your web browser and navigate to `http://localhost:8000`.

## Usage
The dashboard will display 8 gauges that represent temperature readings. The values will be updated in real-time based on the data fetched from the InfluxDB 3 database.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License.