from django.test import TestCase
from .deeplearning.CNNTrain import cnn_train
import os
import django

# Create your tests here.
class CNNTrainTest(TestCase):

    def test_train(self):
       cnn_train(num_workers=1)