const db = db.getSiblingDB("video_tag_db");
db.test.insertOne({ ok: true });

db.createRole({
  role: "videoTagAppRole",
  privileges: [
    {
      resource: { db: "video_tag_db", collection: "" },
      actions: ["find", "insert", "update", "remove", "listCollections", "listIndexes", "createIndex", "dropIndex"]
    }
  ],
  roles: []
});

db.createUser({
  user: "exampleUser001",
  pwd: "examplePassword",
  roles: [
    {
      role: "videoTagAppRole",
      db: "video_tag_db"
    }
  ]
});
