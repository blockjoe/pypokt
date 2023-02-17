import random
import json
from typing import Any, Literal, Optional, OrderedDict, Union

from pydantic import Field, root_validator

from .base import Base, ProtobufBase, ProtobufTypes
from .core import (
    ChainID,
    CoinDenom,
    HashRange,
    MerkleProof,
    ProofT,
    PublicKey,
    TXProof,
    TxResult,
    TxResultMessageTypes,
    SessionHeader,
    Upgrade,
)
from .gov_params import ParamKeys, ParamValueT

import pokt.transactions.messages.proto.tx_signer_pb2 as proto



class Coin(ProtobufBase):

    __protobuf_model__ = proto.Coin

    amount: Optional[str] = None
    denom: Optional[CoinDenom] = "upokt"


class Signature(ProtobufBase):

    __protobuf_model__ = proto.ProtoStdSignature

    pub_key: Optional[str] = Field(
        None, proto_name="publicKey", proto_type=ProtobufTypes.BYTES
    )
    signature: Optional[str] = Field(
        None, proto_name="Signature", proto_type=ProtobufTypes.BYTES
    )


class MsgSendVal(ProtobufBase):

    __amino_ordering__ = ("amount", "from_address", "to_address")
    __protobuf_model__ = proto.MsgSend
    __protobuf_type_url__ = "/x.nodes.MsgSend"

    from_address: Optional[str] = Field(
        None, proto_name="FromAddress", proto_type=ProtobufTypes.BYTES
    )
    to_address: Optional[str] = Field(
        None, proto_name="ToAddress", proto_type=ProtobufTypes.BYTES
    )
    amount: Optional[int] = Field(None, proto_type=ProtobufTypes.STRING)



class MsgAppStakeVal(ProtobufBase):

    __protobuf_model__ = proto.MsgProtoStake
    __protobuf_type_url__ = "/x.apps.MsgProtoStake"

    pubkey: Optional[PublicKey] = Field(None, proto_name="pub_key", proto_type=ProtobufTypes.BYTES)
    chains: Optional[list[str]] = Field(None, proto_type=ProtobufTypes.STRING, proto_repeated=True)
    value: Optional[int] = Field(None, proto_type=ProtobufTypes.STRING)


class MsgBeginAppUnstakeVal(ProtobufBase):

    __protobuf_model__ = proto.MsgBeginUnstake
    __protobuf_type_url__ = "/x.apps.MsgBeginUnstake"

    application_address: Optional[str] = Field(None, proto_name="Address", proto_type=ProtobufTypes.BYTES)


class MsgAppUnjailVal(ProtobufBase):

    __protobuf_model__ = proto.MsgUnjail
    __protobuf_type_url__ = "/x.apps.MsgUnjail"

    address: Optional[str] = Field(
        None, proto_name="AppAddr", proto_type=ProtobufTypes.BYTES
    )


class MsgValidatorStakeVal(ProtobufBase):

    __protobuf_model__ = proto.MsgProtoNodeStake8
    __protobuf_type_url__ = "/x.nodes.MsgProtoStake8"

    public_key: Optional[PublicKey] = Field(
        None, proto_name="Publickey", proto_type=ProtobufTypes.BYTES
    )
    chains: Optional[list[str]] = Field(
        None, proto_name="Chains", proto_type=ProtobufTypes.STRING, proto_repeated=True
    )
    value: Optional[int] = Field(None, proto_type=ProtobufTypes.STRING)
    service_url: Optional[str] = Field(
        None, proto_name="ServiceUrl", proto_type=ProtobufTypes.STRING
    )
    output_address: Optional[str] = Field(
        None, proto_name="OutAddress", proto_type=ProtobufTypes.BYTES
    )


class MsgBeginValidatorUnstakeVal(ProtobufBase):

    __protobuf_model__ = proto.MsgBeginNodeUnstake8
    __protobuf_type_url__ = "/x.nodes.MsgBeginUnstake8"

    validator_address: Optional[str] = Field(
        None, proto_name="Address", proto_type=ProtobufTypes.BYTES
    )
    signer_address: Optional[str] = Field(
        None, proto_name="Signer", proto_type=ProtobufTypes.BYTES
    )


class MsgValidatorUnjailVal(ProtobufBase):

    __protobuf_model__ = proto.MsgNodeUnjail8
    __protobuf_type_url__ = "/x.nodes.MsgUnjail8"

    address: Optional[str] = Field(
        None, proto_name="ValidatorAddr", proto_type=ProtobufTypes.BYTES
    )
    signer_address: Optional[str] = Field(
        None, proto_name="Signer", proto_type=ProtobufTypes.BYTES
    )


class MsgChangeParamVal(ProtobufBase):
    address: Optional[str] = None
    param_key: Optional[ParamKeys] = None
    param_value: Optional[ParamValueT] = None
    # param: SingleParamT


class MsgDaoTransferVal(ProtobufBase):
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    amount: Optional[int] = None
    action: Optional[str] = None


class MsgUpgradeVal(ProtobufBase):
    address: Optional[str] = None
    upgrade: Optional[Upgrade] = None


class MsgProofVal(ProtobufBase):
    merkle_proofs: Optional[MerkleProof] = None
    leaf: Optional[ProofT] = Field(None, discriminator="type_")
    evidence_type: Optional[int] = None  # EvidenceType = None


class MsgClaimVal(ProtobufBase):
    header: SessionHeader
    merkle_root: Optional[HashRange] = None
    total_proofs: Optional[int] = None
    from_address: Optional[str] = None
    evidence_type: Optional[int] = None  # EvidenceType = None
    expiration_height: Optional[int] = None


MsgValT = Union[
    MsgSendVal,
    MsgValidatorStakeVal,
    MsgAppStakeVal,
    MsgValidatorUnjailVal,
    MsgAppUnjailVal,
    MsgBeginValidatorUnstakeVal,
    MsgBeginAppUnstakeVal,
    MsgChangeParamVal,
    MsgUpgradeVal,
    MsgDaoTransferVal,
]


class ProtoStdTx(ProtobufBase):

    __protobuf_model__ = proto.ProtoStdTx

    entropy: Optional[int] = Field(None, proto_type=ProtobufTypes.INT64)
    fee: Optional[list[Coin]] = Field(
        None, proto_type=ProtobufTypes.MESSAGE, proto_repeated=True
    )
    memo: Optional[str] = Field(None, proto_type=ProtobufTypes.STRING)
    msg: Optional[Any] = Field(None, proto_type=ProtobufTypes.ANY)
    signature: Optional[Signature] = Field(None, proto_type=ProtobufTypes.MESSAGE)

class Msg(Base):
    type_: str = Field(..., alias="type")
    value: MsgValT

    entropy: int = 0
    chain_id: ChainID = "mainnet"
    fee: int = 1000
    feeDenom: Optional[CoinDenom] = "upokt"
    memo: Optional[str] = ""


    @root_validator(pre=True)
    def random_entropy(cls, values):
        values["entropy"] = random.randint(-(2**32 - 1), 2**32-1)
        return values

    def _fee(self):
        d = OrderedDict()
        d["fee"] = self.fee
        d["denom"] = self.feeDenom
        return [d]

    def _proto_fee(self) -> list[Coin]:
        return [Coin(amount=str(self.fee), denom=self.feeDenom)]

    def _std_msg_obj(self):
        d = OrderedDict()
        d["type"] = self.type_
        d["value"] = self.value.amino_dict()
        return d

    def std_sign_doc(self) -> bytes:
        d = OrderedDict()
        d["chain_id"] = self.chain_id
        d["entropy"] = self.entropy
        d["fee"] = self._fee()
        d["memo"] = self.memo
        d["msg"] = self._std_msg_obj()
        return json.dumps(d, ensure_ascii=False).encode("utf-8")

    def encode(self, pubkey: str, detached_signature: bytes) -> bytes:
        sig = Signature(pub_key=pubkey, signature=detached_signature.decode("utf-8"))
        stdTx = ProtoStdTx(msg=self.value, entropy=self.entropy, fee=self._proto_fee(), signature=sig, memo=self.memo)
        stdTx_bytes = stdTx.protobuf_message().SerializeToString()
        prefix = str(len(stdTx_bytes)).encode("utf-8")
        return prefix + stdTx_bytes


class MsgClaim(Msg):
    type_: Literal["pocketcore/claim"] = Field(alias="type")
    value: MsgClaimVal


class MsgProof(Msg):
    type_: Literal["pocketcore/proof"] = Field(alias="type")
    value: MsgProofVal


class MsgValidatorStake(Msg):
    type_: Literal["pos/8.0MsgStake", "pos/MsgStake"] = Field(alias="type")
    value: MsgValidatorStakeVal


class MsgBeginValidatorUnstake(Msg):
    type_: Literal["pos/8.0MsgBeginUnstake", "pos/MsgBeginUnstake"] = Field(
        alias="type"
    )
    value: MsgBeginValidatorUnstakeVal


class MsgValidatorUnjail(Msg):
    type_: Literal["pos/MsgUnjail", "pos/8.0MsgUnjail"] = Field(alias="type")
    value: MsgValidatorUnjailVal


class MsgSend(Msg):
    type_: Literal["pos/Send"] = Field("pos/Send", alias="type")
    value: MsgSendVal


class MsgAppStake(Msg):
    type_: Literal["apps/MsgAppStake"] = Field(alias="type")
    value: MsgAppStakeVal


class MsgBeginAppUnstake(Msg):
    type_: Literal["apps/MsgAppBeginUnstake"] = Field(alias="type")
    value: MsgBeginAppUnstakeVal


class MsgAppUnjail(Msg):
    type_: Literal["apps/MsgAppUnjail"] = Field(alias="type")
    value: MsgAppUnjailVal


class MsgDaoTransfer(Msg):
    type_: Literal["gov/msg_dao_transfer"] = Field(alias="type")
    value: MsgDaoTransferVal


class MsgChangeParam(Msg):
    type_: Literal["gov/msg_change_param"] = Field(alias="type")
    value: MsgChangeParamVal


class MsgUpgrade(Msg):
    type_: Literal["gov/msg_upgrade"] = Field(alias="type")
    value: MsgUpgradeVal


MsgT = Union[
    MsgAppStake,
    MsgAppUnjail,
    MsgBeginAppUnstake,
    MsgBeginValidatorUnstake,
    MsgChangeParam,
    MsgClaim,
    MsgDaoTransfer,
    MsgProof,
    MsgSend,
    MsgUpgrade,
    MsgValidatorStake,
    MsgValidatorUnjail,
]



class StdTx(Base):

    entropy: Optional[int] = None
    fee: Optional[list[Coin]] = None
    memo: Optional[str] = None
    msg: Optional[MsgT] = Field(None, discriminator="type_")
    signature: Optional[Signature] = None




class UnconfirmedTransaction(Base):
    hash_: Optional[str] = Field(
        None, alias="hash", description="Hash of the transaction"
    )
    message_type: Optional[TxResultMessageTypes] = Field(
        None,
        description="The type of the transaction",
    )
    stdTx: Optional[StdTx] = None


class Transaction(Base):
    hash_: Optional[str] = Field(
        None, alias="hash", description="Hash of the transaction"
    )
    height: Optional[int] = Field(None, description="Blockheight of the transaction")
    index: Optional[int] = None
    tx_result: Optional[TxResult] = None
    tx: Optional[str] = Field(None, description="Raw data of the transaction")
    proof: Optional[TXProof] = None
    stdTx: Optional[StdTx] = None
