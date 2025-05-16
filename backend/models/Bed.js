const mongoose = require('mongoose');

const bedSchema = new mongoose.Schema({
  roomId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Room',
    required: true,
  },
  bedNumber: {
    type: String,
    required: true,
  },
  status: {
    type: String,
    enum: ['occupied', 'vacant'],
    default: 'vacant',
  },
  tenantId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Tenant',
  },
});

module.exports = mongoose.model('Bed', bedSchema);