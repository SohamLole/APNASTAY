const mongoose = require('mongoose');

const roomSchema = new mongoose.Schema({
  buildingId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Building',
    required: true,
  },
  name: {
    type: String,
    required: true,
  },
  type: {
    type: String,
    enum: ['2-Sharing', '3-Sharing', '4-Sharing', 'Private'],
    required: true,
  },
  capacity: {
    type: Number,
    required: true,
  },
});

module.exports = mongoose.model('Room', roomSchema);