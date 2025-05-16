const mongoose = require('mongoose');

const paymentSchema = new mongoose.Schema({
  tenantId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Tenant',
    required: true,
  },
  month: {
    type: Number,
    required: true,
    min: 1,
    max: 12,
  },
  year: {
    type: Number,
    required: true,
  },
  amountDue: {
    type: Number,
    required: true,
  },
  amountPaid: {
    type: Number,
    required: true,
    default: 0,
  },
  paymentDate: {
    type: Date,
  },
  status: {
    type: String,
    enum: ['paid', 'unpaid', 'partial'],
    default: 'unpaid',
  },
});

module.exports = mongoose.model('Payment', paymentSchema);