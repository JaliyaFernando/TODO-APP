const express = require("express");
const TodoRoute = express.Router();

const TodoController = require("../controller/TodoController");

TodoRoute.post("/add", TodoController.addTodo);

module.exports = TodoRoute;