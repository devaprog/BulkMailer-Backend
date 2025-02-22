import email
import re
from datetime import timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from rest_framework import serializers

from .models import *
from .task import *


class OTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTP
        fields = ["email"]

    def validate(self, data):
        email = data["email"]
        if not re.findall("@.", email):
            raise ValidationError(("Enter a valid email"))
        user = list(NewUserResgistration.objects.filter(email=email))
        if user != []:
            raise ValidationError({"msg": "User already exists"})
        return data

    def create(self, data):
        userOTP = OTP.objects.filter(email=data["email"])
        if userOTP is not None:
            userOTP.delete()
        email = data["email"]
        OTP.objects.create(email=email)
        send_otp.delay(email)

        return data


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.CharField(write_only=True)
    otp = serializers.CharField(write_only=True)

    def validate(self, data):
        userOTP = OTP.objects.get(email=data["email"])

        if not userOTP.otp == data["otp"]:
            context = {"msg": "OTP incorrect"}
            raise ValidationError((context))
        if userOTP.time + timedelta(minutes=3) < timezone.now():
            context = {"msg": "OTP Timed Out"}
            userOTP.delete()
            raise ValidationError((context))
        userOTP.is_verified = True
        userOTP.save()
        return {"msg": "done"}

    def create(self, validated_data):
        return validated_data


class NewUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewUserResgistration
        fields = ["id", "name", "user_name", "email", "password"]
        extra_kwargs = {
            "password": {"write_only": True},
        }

    @staticmethod
    def validate_password(data):
        if (
            len(data) < 8
            or not re.findall(r"\d", data)
            or not re.findall("[A-Z]", data)
            or not re.findall("[a-z]", data)
            or not re.findall(r"[()[\]{}|\\`~!@#$%^&*_\-+=;:'\",<>./?]", data)
        ):
            raise ValidationError(
                {
                    "msg": "The password needs to be more than 8 characters, contain atleast one uppercase,one lowercase and a special character"
                }
            )

        return data

    @staticmethod
    def validate_email(data):
        try:
            userOTP = OTP.objects.get(email=data)
        except:
            context = {"msg": "Please raise OTP for email verification"}
            raise ValidationError(context)
        if userOTP.is_verified is False:
            context = {"msg": "Please verify your email first"}
            raise ValidationError(context)
        return data

    def create(self, data):
        userOTP = OTP.objects.get(email=data["email"])
        user = NewUserResgistration.objects.create(
            name=data["name"],
            user_name=data["user_name"],
            email=data["email"],
            password=data["password"],
        )
        user.password = make_password(data["password"])
        user.is_active = True
        user.save()
        userOTP.delete()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True)
    refresh = serializers.CharField(read_only=True)
    access = serializers.CharField(read_only=True)

    def validate(self, data):
        try:
            NewUserResgistration.objects.get(email=data["email"])
        except:
            raise ValidationError({"msg": "User Doesn’t Exist"})

        user = authenticate(email=data["email"], password=data["password"])

        if not user:
            raise ValidationError({"msg": "Invalid Credentials"})
        data["refresh"] = user.refresh
        data["access"] = user.access
        return data

    def create(self, validated_data):
        return validated_data


class ChangePasswordSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewUserResgistration
        fields = ["email", "password"]

    @staticmethod
    def validate_email(data):
        try:
            userOTP = OTP.objects.get(email=data)
        except:
            context = {"msg": "Please raise OTP for email verification"}
            raise ValidationError(context)
        if userOTP.is_verified is False:
            context = {"msg": "Please verify your email first"}
            raise ValidationError(context)
        return data

    def validate(self, data):
        newPassword = data["password"]
        userEmail = data["email"]

        if (
            len(newPassword) < 8
            or not re.findall(r"\d", newPassword)
            or not re.findall("[A-Z]", newPassword)
            or not re.findall("[a-z]", newPassword)
            or not re.findall(r"[()[\]{}|\\`~!@#$%^&*_\-+=;:'\",<>./?]", newPassword)
        ):
            raise ValidationError(
                {
                    "msg": "The password needs to be more than 8 characters, contain atleast one uppercase,one lowercase and a special character"
                }
            )
        user = authenticate(email=userEmail, password=newPassword)

        if user is not None:
            context = {"msg": "New password cannot be the same as old password."}
            raise ValidationError(context)
        return data

    def update(self, instance, validated_data):
        userOTP = OTP.objects.get(email=validated_data.get("email"))
        instance.password = make_password(validated_data.get("password"))
        instance.save()
        userOTP.delete()
        return instance


class ResetPasswordViewOTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTP
        fields = ["email"]

    def validate(self, data):
        email = data["email"]
        if not re.findall("@.", email):
            raise ValidationError({"msg": "Enter a valid email"})
        try:
            NewUserResgistration.objects.get(email=email)
        except:
            raise ValidationError({"msg": "User Does not exists with the given email"})
        return data

    def create(self, data):
        userOTP = OTP.objects.filter(email=data["email"])
        if userOTP is not None:
            userOTP.delete()
        email = data["email"]
        OTP.objects.create(email=email)
        send_otp(email)

        return data


class GmailAPPModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = GmailAPPModel
        fields = "__all__"

    def validate(self, data):
        email = data["email"]
        if not re.findall("@.", email):
            raise ValidationError({"msg": "Enter a valid email"})
        if GmailAPPModel.objects.filter(email=email).exists():
            raise ValidationError({"msg": "Entered mail already exists"})
        return data


class UpdateAppPasswordSerializer(serializers.ModelSerializer):
    class Meta:
        model = GmailAPPModel
        fields = ["email", "app_password"]

    @staticmethod
    def validated(data):
        email = data["email"]

        try:
            appGmail = GmailAPPModel.objects.get(email=email)
        except:
            raise ValidationError(
                {"msg": "App Password with this email does not exists"}
            )

        if appGmail.app_password == data["app_password"]:
            raise ValidationError({"msg": "Password is same as old one"})
        return data


class ProfileDetailsUpdateSerializer(serializers.ModelSerializer):
    AppPassword = serializers.SerializerMethodField()

    class Meta:
        model = NewUserResgistration
        fields = ["email", "name", "user_name", "gender", "mobile", "AppPassword"]

        extra_kwargs = {
            "email": {"read_only": True},
        }

    @staticmethod
    def get_AppPassword(obj):
        try:
            GmailAPPModel.objects.get(id=obj.id)
            return True
        except:
            return False
