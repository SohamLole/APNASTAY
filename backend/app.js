const express = require('express');
const morgan = require('morgan');
const cors = require('cors');
const helmet = require('helmet');
const errorHandler = require('./middleware/error');

// Route files
const auth = require('./routes/authRoutes');
const tenants = require('./routes/tenantRoutes');
const beds = require('./routes/bedRoutes');
const buildings = require('./routes/buildingRoutes');
const rooms = require('./routes/roomRoutes');
const payments = require('./routes/paymentRoutes');

const app = express();

// Body parser
app.use(express.json());

// Dev logging middleware
if (process.env.NODE_ENV === 'development') {
  app.use(morgan('dev'));
}

// Enable CORS
app.use(cors());

// Set security headers
app.use(helmet());

// Mount routers
app.use('/api/auth', auth);
app.use('/api/tenants', tenants);
app.use('/api/beds', beds);
app.use('/api/buildings', buildings);
app.use('/api/rooms', rooms);
app.use('/api/payments', payments);

// Error handler middleware
app.use(errorHandler);

module.exports = app;